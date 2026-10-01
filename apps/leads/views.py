import csv

from django.http import HttpResponse
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import RoleCode, User
from apps.audit.services import log_action
from apps.leads.filters import LeadFilter
from apps.leads.models import Lead, LeadNote, LeadStatus
from apps.leads.permissions import LeadObjectPermission
from apps.leads.serializers import (
    LeadAssignSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    LeadNoteCreateSerializer,
    LeadNoteSerializer,
    LeadStatusUpdateSerializer,
    LeadUpdateSerializer,
    PublicLeadCreateSerializer,
)
from apps.leads.services.assign_lead import assign_lead
from apps.leads.services.change_status import change_status
from apps.leads.services.create_lead import create_lead
from apps.leads.throttles import PublicLeadRateThrottle
from apps.notifications.models import MessageEvent
from apps.notifications.services import dispatch, send_lead_assigned_notification
from common.mixins import EnvelopeMixin
from common.permissions import CRM_ROLES, MANAGER_ROLES, IsCrmUser
from common.responses import success_response


class PublicLeadCreateView(EnvelopeMixin, generics.CreateAPIView):
    """POST /api/v1/public/leads/ — internet-facing enquiry submission."""

    serializer_class = PublicLeadCreateSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PublicLeadRateThrottle]
    success_message = "Enquiry submitted successfully."

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = create_lead(dict(serializer.validated_data), request=request)
        # Acknowledge on the channels the visitor consented to in the enquiry form.
        dispatch(
            MessageEvent.ENQUIRY_RECEIVED,
            email=lead.email or None,
            phone=lead.phone if lead.preferred_contact_method == "WHATSAPP" else None,
            context={
                "full_name": f"{lead.first_name} {lead.last_name}".strip(),
                "first_name": lead.first_name,
                "lead_number": lead.lead_number,
            },
            link="/",
        )
        log_action(
            action="LEAD_CREATED",
            entity_type="Lead",
            entity_id=lead.id,
            new_values={"lead_number": lead.lead_number, "source": lead.source},
            request=request,
        )
        # Never expose internal lead IDs or sales data to the public caller.
        return Response(
            {
                "lead_number": lead.lead_number,
                "message": "Thank you, our team will contact you shortly.",
            },
            status=status.HTTP_201_CREATED,
        )


class LeadViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, LeadObjectPermission]
    filterset_class = LeadFilter
    search_fields = ["lead_number", "first_name", "last_name", "phone", "email", "city"]
    ordering_fields = ["created_at", "status", "priority"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Lead.objects.select_related(
            "product", "campaign", "assigned_to"
        ).prefetch_related("status_history", "notes")
        user = self.request.user
        if user.role == RoleCode.SALES_EXECUTIVE:
            queryset = queryset.filter(assigned_to=user)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        if self.action in ("update", "partial_update"):
            return LeadUpdateSerializer
        return LeadDetailSerializer

    def perform_update(self, serializer):
        old_values = LeadDetailSerializer(self.get_object()).data
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="LEAD_UPDATED",
            entity_type="Lead",
            entity_id=instance.id,
            old_values=old_values,
            new_values=serializer.data,
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        if not request.user.has_role(*MANAGER_ROLES):
            return Response(
                {
                    "success": False,
                    "message": "Not permitted to assign leads.",
                    "errors": {},
                    "code": "FORBIDDEN",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        lead = self.get_object()
        serializer = LeadAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            assigned_user = User.objects.get(id=serializer.validated_data["assigned_to"])
        except User.DoesNotExist as exc:
            raise ValidationError({"assigned_to": ["User not found."]}) from exc
        if not assigned_user.has_role(*CRM_ROLES):
            raise ValidationError({"assigned_to": ["Leads can only be assigned to CRM users."]})

        assign_lead(lead, assigned_user, changed_by=request.user)
        send_lead_assigned_notification(lead, assigned_user)
        log_action(
            actor=request.user,
            action="LEAD_ASSIGNED",
            entity_type="Lead",
            entity_id=lead.id,
            new_values={"assigned_to": str(assigned_user.id)},
            request=request,
        )
        return success_response(
            LeadDetailSerializer(lead).data, message="Lead assigned successfully."
        )

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if new_status not in LeadStatus.values:
            raise ValidationError({"status": ["Invalid lead status."]})

        old_status = lead.status
        change_status(
            lead,
            new_status,
            changed_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        log_action(
            actor=request.user,
            action="LEAD_STATUS_CHANGED",
            entity_type="Lead",
            entity_id=lead.id,
            old_values={"status": old_status},
            new_values={"status": new_status},
            request=request,
        )
        return success_response(LeadDetailSerializer(lead).data, message="Lead status updated.")

    @action(detail=True, methods=["post"])
    def notes(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = LeadNote.objects.create(
            lead=lead, created_by=request.user, note=serializer.validated_data["note"]
        )
        log_action(
            actor=request.user,
            action="LEAD_NOTE_ADDED",
            entity_type="Lead",
            entity_id=lead.id,
            new_values={"note_id": str(note.id)},
            request=request,
        )
        return success_response(
            LeadNoteSerializer(note).data,
            message="Note added.",
            status_code=status.HTTP_201_CREATED,
        )


class LeadExportView(generics.ListAPIView):
    """GET /api/v1/reports/export/ — CSV export of leads visible to the caller."""

    permission_classes = [permissions.IsAuthenticated, IsCrmUser]
    filterset_class = LeadFilter
    search_fields = ["lead_number", "first_name", "last_name", "phone", "email", "city"]

    def get_queryset(self):
        queryset = Lead.objects.select_related("product", "campaign", "assigned_to")
        user = self.request.user
        if user.role == RoleCode.SALES_EXECUTIVE:
            queryset = queryset.filter(assigned_to=user)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="leads_export.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Lead Number",
                "Name",
                "Phone",
                "City",
                "Product",
                "Source",
                "Status",
                "Priority",
                "Assigned To",
                "Created At",
            ]
        )
        for lead in queryset:
            writer.writerow(
                [
                    lead.lead_number,
                    f"{lead.first_name} {lead.last_name}".strip(),
                    lead.phone,
                    lead.city or "",
                    lead.product.name,
                    lead.source,
                    lead.status,
                    lead.priority,
                    lead.assigned_to.full_name if lead.assigned_to else "",
                    lead.created_at.isoformat(),
                ]
            )
        log_action(
            actor=request.user,
            action="LEADS_EXPORTED",
            entity_type="Lead",
            entity_id="bulk",
            request=request,
        )
        return response
