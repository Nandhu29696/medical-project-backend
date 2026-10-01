from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action

from apps.accounts.models import RoleCode
from apps.audit.services import log_action
from apps.followups.models import FollowUp, FollowUpStatus
from apps.followups.serializers import FollowUpCompleteSerializer, FollowUpSerializer
from common.mixins import EnvelopeMixin
from common.permissions import IsCrmUser
from common.responses import success_response


class FollowUpViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    serializer_class = FollowUpSerializer
    permission_classes = [permissions.IsAuthenticated, IsCrmUser]
    filterset_fields = ["status", "assigned_to", "lead"]
    ordering_fields = ["scheduled_at", "created_at"]

    def get_queryset(self):
        queryset = FollowUp.objects.select_related("lead", "assigned_to")
        user = self.request.user
        if user.role == RoleCode.SALES_EXECUTIVE:
            queryset = queryset.filter(assigned_to=user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(
            assigned_to=serializer.validated_data.get("assigned_to") or self.request.user
        )
        log_action(
            actor=self.request.user,
            action="FOLLOWUP_CREATED",
            entity_type="FollowUp",
            entity_id=instance.id,
            new_values=serializer.data,
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        followup = self.get_object()
        serializer = FollowUpCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        followup.status = FollowUpStatus.COMPLETED
        followup.completed_at = timezone.now()
        followup.outcome = serializer.validated_data["outcome"]
        followup.notes = serializer.validated_data.get("notes", followup.notes)
        followup.save(update_fields=["status", "completed_at", "outcome", "notes", "updated_at"])
        log_action(
            actor=request.user,
            action="FOLLOWUP_COMPLETED",
            entity_type="FollowUp",
            entity_id=followup.id,
            request=request,
        )
        return success_response(
            FollowUpSerializer(followup).data, message="Follow-up marked as completed."
        )
