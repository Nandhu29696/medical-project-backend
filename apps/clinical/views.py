from datetime import datetime, time, timedelta

import django_filters
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.audit.services import log_action
from apps.clinical.models import (
    Consultation,
    ConsultationStatus,
    DoctorProfile,
    MedicalDocument,
    PatientProfile,
    PrescriptionItem,
    VitalReading,
)
from apps.clinical.serializers import (
    BookingSerializer,
    ConsultationSerializer,
    DoctorProfileSerializer,
    DoctorSelfUpdateSerializer,
    MedicalDocumentSerializer,
    PatientClinicalUpdateSerializer,
    PatientPhotoSerializer,
    PatientProfileSerializer,
    PrescriptionUpdateSerializer,
    PublicDoctorSerializer,
    VitalReadingSerializer,
)
from apps.notifications.models import MessageEvent, NotificationCategory
from apps.notifications.services import consultation_context, dispatch, notify
from common.mixins import EnvelopeMixin
from common.permissions import ADMIN_ROLES, IsAdmin, IsClinicalStaff, user_has_role
from common.responses import success_response

# Bookable consultation slots (clinic local time, see settings.TIME_ZONE).
SLOT_START = time(10, 0)
SLOT_END = time(17, 0)
SLOT_MINUTES = 30
ACTIVE_STATUSES = (ConsultationStatus.SCHEDULED, ConsultationStatus.COMPLETED)


def visible_patients(user):
    """Admins see every patient, doctors see their own patients, patients see themselves."""
    queryset = PatientProfile.objects.select_related("user", "assigned_doctor", "source_lead")
    if user.has_role(*ADMIN_ROLES):
        return queryset
    scope = Q(pk__in=[])
    if user.has_role(RoleCode.DOCTOR):
        scope |= Q(assigned_doctor=user) | Q(user__patient_consultations__doctor=user)
    if user.has_role(RoleCode.PATIENT):
        scope |= Q(user=user)
    return queryset.filter(scope).distinct()


def visible_consultations(user):
    queryset = Consultation.objects.select_related(
        "patient", "doctor", "doctor__doctor_profile", "patient__patient_profile"
    ).prefetch_related("prescription_items")
    if user.has_role(*ADMIN_ROLES):
        return queryset
    scope = Q(pk__in=[])
    if user.has_role(RoleCode.DOCTOR):
        scope |= Q(doctor=user)
    if user.has_role(RoleCode.PATIENT):
        scope |= Q(patient=user)
    return queryset.filter(scope)


def _can_edit_consultation(user, consultation):
    return user.has_role(*ADMIN_ROLES) or consultation.doctor_id == user.id


def doctor_slots(doctor_user, day):
    """Every bookable slot on `day` for a doctor, flagged available or not."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, SLOT_START), tz)
    end = timezone.make_aware(datetime.combine(day, SLOT_END), tz)
    taken = set(
        Consultation.objects.filter(
            doctor=doctor_user,
            status__in=ACTIVE_STATUSES,
            scheduled_at__gte=start,
            scheduled_at__lt=end,
        ).values_list("scheduled_at", flat=True)
    )
    now = timezone.now()
    slots = []
    current = start
    while current < end:
        slots.append(
            {"start": current.isoformat(), "available": current > now and current not in taken}
        )
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


def _is_valid_slot(moment):
    local = timezone.localtime(moment)
    return (
        SLOT_START <= local.time() < SLOT_END
        and local.minute % SLOT_MINUTES == 0
        and local.second == 0
        and local.microsecond == 0
    )


class DoctorViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    """Doctor directory: every signed-in user can read it; only admins can edit it."""

    queryset = DoctorProfile.objects.select_related("user").filter(user__is_active=True)
    serializer_class = DoctorProfileSerializer
    filterset_fields = ["specialization", "is_available"]
    search_fields = ["user__first_name", "user__last_name", "specialization", "clinic_name"]
    ordering_fields = ["years_of_experience", "created_at"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        """GET/PATCH /api/v1/doctors/me/ — the signed-in doctor's own profile."""
        profile = DoctorProfile.objects.filter(user=request.user).first()
        if profile is None:
            raise NotFound("No doctor profile for this account.")
        if request.method == "PATCH":
            serializer = DoctorSelfUpdateSerializer(
                profile, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return success_response(serializer.data, message="Profile updated.")
        return success_response(DoctorProfileSerializer(profile, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None):
        """GET /api/v1/doctors/{id}/slots/?date=YYYY-MM-DD — 30-minute slots, 10:00–17:00."""
        profile = self.get_object()
        raw = request.query_params.get("date")
        try:
            day = datetime.strptime(raw, "%Y-%m-%d").date() if raw else timezone.localdate()
        except ValueError as exc:
            raise ValidationError({"date": ["Use YYYY-MM-DD."]}) from exc
        return success_response(
            {
                "date": day.isoformat(),
                "doctor_id": str(profile.user_id),
                "slots": doctor_slots(profile.user, day),
            }
        )


class PublicDoctorListView(generics.ListAPIView):
    """Public website doctor showcase — no contact or registration details."""

    queryset = DoctorProfile.objects.select_related("user").filter(user__is_active=True)
    serializer_class = PublicDoctorSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = None


class PatientViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    filterset_fields = ["gender", "blood_group", "assigned_doctor"]
    search_fields = ["patient_code", "user__first_name", "user__last_name", "user__email", "city"]
    ordering_fields = ["created_at", "patient_code"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return visible_patients(self.request.user)

    def get_permissions(self):
        if self.action in ("create", "destroy"):
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.action in ("update", "partial_update"):
            return [permissions.IsAuthenticated(), IsClinicalStaff()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        user = self.request.user
        if self.action in ("update", "partial_update") and not user.has_role(*ADMIN_ROLES):
            return PatientClinicalUpdateSerializer
        return PatientProfileSerializer

    def perform_create(self, serializer):
        if PatientProfile.objects.filter(user=serializer.validated_data["user"]).exists():
            raise ValidationError({"user_id": ["This user already has a patient profile."]})
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="PATIENT_CREATED",
            entity_type="PatientProfile",
            entity_id=instance.id,
            new_values={"patient_code": instance.patient_code},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        if not user.has_role(*ADMIN_ROLES) and instance.assigned_doctor_id != user.id:
            raise PermissionDenied("Only the assigned doctor can update this patient's record.")
        serializer.save()
        log_action(
            actor=user,
            action="PATIENT_UPDATED",
            entity_type="PatientProfile",
            entity_id=instance.id,
            request=self.request,
        )

    def _own_profile(self, request):
        profile = visible_patients(request.user).filter(user=request.user).first()
        if profile is None:
            raise NotFound("No patient profile for this account.")
        return profile

    @action(detail=False, methods=["get"])
    def me(self, request):
        """GET /api/v1/patients/me/ — the signed-in patient's own profile."""
        return success_response(
            PatientProfileSerializer(self._own_profile(request), context={"request": request}).data
        )

    @action(detail=False, methods=["post"], url_path="me/photo")
    def my_photo(self, request):
        """POST /api/v1/patients/me/photo/ (multipart `photo`) — patient updates own photo."""
        serializer = PatientPhotoSerializer(
            self._own_profile(request), data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, message="Photo updated.")


class ConsultationFilter(django_filters.FilterSet):
    scheduled_after = django_filters.IsoDateTimeFilter(field_name="scheduled_at", lookup_expr="gte")
    scheduled_before = django_filters.IsoDateTimeFilter(field_name="scheduled_at", lookup_expr="lt")
    follow_up_before = django_filters.DateFilter(field_name="follow_up_date", lookup_expr="lte")
    follow_up_after = django_filters.DateFilter(field_name="follow_up_date", lookup_expr="gte")

    class Meta:
        model = Consultation
        fields = ["status", "mode", "doctor", "patient"]


class ConsultationViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    serializer_class = ConsultationSerializer
    filterset_class = ConsultationFilter
    ordering_fields = ["scheduled_at", "created_at"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return visible_consultations(self.request.user)

    def get_permissions(self):
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), IsAdmin()]
        if self.action in ("create", "update", "partial_update", "prescription"):
            return [permissions.IsAuthenticated(), IsClinicalStaff()]
        return [permissions.IsAuthenticated()]

    def _notify_booking(self, consultation, booked_by_patient=False):
        ctx = consultation_context(consultation)
        when = f"{ctx['date']}, {ctx['time']}"
        link = f"/consultations/{consultation.id}"
        dispatch(
            MessageEvent.DOCTOR_NEW_BOOKING,
            user=consultation.doctor,
            context=ctx,
            link=link,
            in_app={
                "title": (
                    "New consultation booked" if booked_by_patient else "Consultation scheduled"
                ),
                "message": f"{consultation.patient.full_name} — {when}",
            },
            category=NotificationCategory.CONSULTATION,
        )
        dispatch(
            MessageEvent.CONSULTATION_BOOKED,
            user=consultation.patient,
            context=ctx,
            link=link,
            in_app={
                "title": "Consultation confirmed",
                "message": f"With Dr. {consultation.doctor.full_name} on {when}",
            },
            category=NotificationCategory.CONSULTATION,
        )

    def _notify_cancelled(self, consultation):
        ctx = consultation_context(consultation)
        dispatch(
            MessageEvent.CONSULTATION_CANCELLED,
            user=consultation.patient,
            context=ctx,
            link="/book",
            in_app={
                "title": "Consultation cancelled",
                "message": f"Dr. {ctx['doctor_name']} · {ctx['date']} at {ctx['time']}",
            },
            category=NotificationCategory.CONSULTATION,
        )

    def perform_create(self, serializer):
        user = self.request.user
        if user.has_role(*ADMIN_ROLES):
            if "doctor" not in serializer.validated_data:
                raise ValidationError({"doctor_id": ["This field is required."]})
            instance = serializer.save(created_by=user)
        else:
            # Doctors can only book consultations for themselves.
            instance = serializer.save(doctor=user, created_by=user)
        self._notify_booking(instance)
        log_action(
            actor=user,
            action="CONSULTATION_CREATED",
            entity_type="Consultation",
            entity_id=instance.id,
            request=self.request,
        )

    def perform_update(self, serializer):
        user = self.request.user
        if not user.has_role(*ADMIN_ROLES):
            if serializer.instance.doctor_id != user.id:
                raise PermissionDenied("You can only update your own consultations.")
            if serializer.validated_data.get("doctor", user) != user:
                raise PermissionDenied("You cannot reassign a consultation to another doctor.")
        was_cancelled = serializer.instance.status == ConsultationStatus.CANCELLED
        instance = serializer.save()
        if instance.status == ConsultationStatus.CANCELLED and not was_cancelled:
            self._notify_cancelled(instance)
        log_action(
            actor=user,
            action="CONSULTATION_UPDATED",
            entity_type="Consultation",
            entity_id=instance.id,
            request=self.request,
        )

    @action(detail=False, methods=["post"])
    def book(self, request):
        """POST /api/v1/consultations/book/ — a patient books an open slot for themselves."""
        if not user_has_role(request.user, RoleCode.PATIENT):
            raise PermissionDenied("Only patients can book consultations here.")
        serializer = BookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not _is_valid_slot(data["scheduled_at"]):
            raise ValidationError({"scheduled_at": ["Pick one of the offered time slots."]})
        with transaction.atomic():
            clash = (
                Consultation.objects.select_for_update()
                .filter(
                    doctor=data["doctor_id"],
                    scheduled_at=data["scheduled_at"],
                    status__in=ACTIVE_STATUSES,
                )
                .exists()
            )
            if clash:
                raise ValidationError({"scheduled_at": ["That slot has just been taken."]})
            consultation = Consultation.objects.create(
                patient=request.user,
                doctor=data["doctor_id"],
                scheduled_at=data["scheduled_at"],
                mode=data["mode"],
                chief_complaint=data["chief_complaint"],
                created_by=request.user,
            )
        profile = PatientProfile.objects.filter(user=request.user, assigned_doctor=None).first()
        if profile:
            profile.assigned_doctor = consultation.doctor
            profile.save(update_fields=["assigned_doctor", "updated_at"])
        self._notify_booking(consultation, booked_by_patient=True)
        log_action(
            actor=request.user,
            action="CONSULTATION_BOOKED",
            entity_type="Consultation",
            entity_id=consultation.id,
            request=request,
        )
        consultation = self.get_queryset().get(pk=consultation.pk)
        return success_response(
            ConsultationSerializer(consultation, context={"request": request}).data,
            message="Consultation booked.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def prescription(self, request, pk=None):
        """POST /api/v1/consultations/{id}/prescription/ {"items": [...]} — replace medicines."""
        consultation = self.get_object()
        if not _can_edit_consultation(request.user, consultation):
            raise PermissionDenied("You can only prescribe on your own consultations.")
        serializer = PrescriptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            consultation.prescription_items.all().delete()
            for index, item in enumerate(serializer.validated_data["items"]):
                item["sort_order"] = index
                PrescriptionItem.objects.create(consultation=consultation, **item)
        dispatch(
            MessageEvent.PRESCRIPTION_READY,
            user=consultation.patient,
            context=consultation_context(consultation),
            link=f"/consultations/{consultation.id}",
            in_app={
                "title": "New prescription",
                "message": f"Dr. {consultation.doctor.full_name} updated your prescription.",
            },
            category=NotificationCategory.PRESCRIPTION,
        )
        log_action(
            actor=request.user,
            action="PRESCRIPTION_UPDATED",
            entity_type="Consultation",
            entity_id=consultation.id,
            request=request,
        )
        consultation = self.get_queryset().get(pk=consultation.pk)
        return success_response(
            ConsultationSerializer(consultation, context={"request": request}).data,
            message="Prescription saved.",
        )


def _check_patient_write_access(user, patient_profile):
    """Admins: any patient. Doctors: their visible patients. Patients: only themselves."""
    if not visible_patients(user).filter(pk=patient_profile.pk).exists():
        raise PermissionDenied("You cannot add records for this patient.")
    if user.has_role(*ADMIN_ROLES, RoleCode.DOCTOR):
        return
    if patient_profile.user_id != user.id:
        raise PermissionDenied("You cannot add records for this patient.")


class PatientRecordViewSet(
    EnvelopeMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Shared scoping for documents and vitals: records of patients the caller can see."""

    model = None
    filterset_fields = ["patient"]
    owner_field = "uploaded_by"

    def get_queryset(self):
        return self.model.objects.select_related("patient__user").filter(
            patient__in=visible_patients(self.request.user)
        )

    def perform_create(self, serializer):
        _check_patient_write_access(self.request.user, serializer.validated_data["patient"])
        instance = serializer.save(**{self.owner_field: self.request.user})
        self.after_create(instance)

    def after_create(self, instance):
        pass

    def perform_destroy(self, instance):
        user = self.request.user
        if (
            not user.has_role(*ADMIN_ROLES)
            and getattr(instance, f"{self.owner_field}_id") != user.id
        ):
            raise PermissionDenied("Only the person who added this record can delete it.")
        instance.delete()


class MedicalDocumentViewSet(PatientRecordViewSet):
    model = MedicalDocument
    serializer_class = MedicalDocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["patient", "document_type"]
    owner_field = "uploaded_by"

    def after_create(self, instance):
        recipients = {instance.patient.user, instance.patient.assigned_doctor} - {
            self.request.user,
            None,
        }
        in_app = {
            "title": "New document uploaded",
            "message": f"{instance.title} — {instance.patient.user.full_name}",
        }
        for recipient in recipients:
            if recipient == instance.patient.user:
                # The patient also gets email / WhatsApp per their preferences.
                dispatch(
                    MessageEvent.DOCUMENT_UPLOADED,
                    user=recipient,
                    context={"document_title": instance.title},
                    link="/my-health",
                    in_app=in_app,
                    category=NotificationCategory.DOCUMENT,
                )
            else:
                notify(
                    recipient,
                    in_app["title"],
                    in_app["message"],
                    link=f"/patients/{instance.patient_id}",
                    category=NotificationCategory.DOCUMENT,
                )


class VitalReadingViewSet(PatientRecordViewSet):
    model = VitalReading
    serializer_class = VitalReadingSerializer
    owner_field = "recorded_by"
    ordering_fields = ["recorded_at"]


class ClinicalSummaryView(APIView):
    """GET /api/v1/clinical/summary/ — counts scoped to what the caller may see."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        consultations = visible_consultations(user)
        now = timezone.now()
        today = timezone.localdate()
        day_start = timezone.make_aware(datetime.combine(today, time.min))
        data = {
            "patients": visible_patients(user).count(),
            "doctors": DoctorProfile.objects.filter(user__is_active=True).count(),
            "upcoming_consultations": consultations.filter(
                status=ConsultationStatus.SCHEDULED, scheduled_at__gte=now
            ).count(),
            "today_consultations": consultations.filter(
                scheduled_at__gte=day_start, scheduled_at__lt=day_start + timedelta(days=1)
            ).count(),
            "completed_consultations": consultations.filter(
                status=ConsultationStatus.COMPLETED
            ).count(),
            "total_consultations": consultations.count(),
            "follow_ups_due": consultations.filter(
                status=ConsultationStatus.COMPLETED,
                follow_up_date__gte=today,
                follow_up_date__lte=today + timedelta(days=7),
            ).count(),
        }
        return success_response(data)
