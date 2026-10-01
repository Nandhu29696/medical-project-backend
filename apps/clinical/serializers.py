from datetime import date

from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import RoleCode, User
from apps.clinical.models import (
    Consultation,
    ConsultationMode,
    DoctorProfile,
    MedicalDocument,
    PatientProfile,
    PrescriptionItem,
    VitalReading,
)


class UserBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone")


def _users_with_role(code):
    return User.objects.filter(roles__code=code, is_active=True)


class DoctorProfileSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=_users_with_role(RoleCode.DOCTOR), write_only=True
    )

    class Meta:
        model = DoctorProfile
        fields = (
            "id",
            "user",
            "user_id",
            "specialization",
            "qualification",
            "registration_number",
            "years_of_experience",
            "clinic_name",
            "consultation_fee",
            "bio",
            "photo",
            "is_available",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class DoctorSelfUpdateSerializer(serializers.ModelSerializer):
    """Fields a doctor may change on their own profile."""

    class Meta:
        model = DoctorProfile
        fields = ("bio", "photo", "is_available", "clinic_name", "consultation_fee")

    def to_representation(self, instance):
        return DoctorProfileSerializer(instance, context=self.context).data


class PublicDoctorSerializer(serializers.ModelSerializer):
    """Safe subset for the public website — no email, phone or registration number."""

    name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = DoctorProfile
        fields = (
            "id",
            "name",
            "specialization",
            "qualification",
            "years_of_experience",
            "clinic_name",
            "bio",
            "photo",
            "is_available",
        )


class PatientProfileSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user", queryset=_users_with_role(RoleCode.PATIENT), write_only=True
    )
    assigned_doctor = UserBriefSerializer(read_only=True)
    assigned_doctor_id = serializers.PrimaryKeyRelatedField(
        source="assigned_doctor",
        queryset=_users_with_role(RoleCode.DOCTOR),
        write_only=True,
        required=False,
        allow_null=True,
    )
    age = serializers.SerializerMethodField()
    source_lead_number = serializers.CharField(
        source="source_lead.lead_number", read_only=True, default=None
    )

    class Meta:
        model = PatientProfile
        fields = (
            "id",
            "patient_code",
            "user",
            "user_id",
            "date_of_birth",
            "age",
            "gender",
            "blood_group",
            "address",
            "city",
            "state",
            "emergency_contact_name",
            "emergency_contact_phone",
            "medical_history",
            "allergies",
            "current_medications",
            "photo",
            "assigned_doctor",
            "assigned_doctor_id",
            "source_lead",
            "source_lead_number",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "patient_code", "created_at", "updated_at")

    def get_age(self, obj):
        if not obj.date_of_birth:
            return None
        today = date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class PatientClinicalUpdateSerializer(serializers.ModelSerializer):
    """The subset of a patient profile a treating doctor may edit."""

    class Meta:
        model = PatientProfile
        fields = ("medical_history", "allergies", "current_medications")

    def to_representation(self, instance):
        return PatientProfileSerializer(instance, context=self.context).data


class PatientPhotoSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField()

    class Meta:
        model = PatientProfile
        fields = ("photo",)

    def to_representation(self, instance):
        return PatientProfileSerializer(instance, context=self.context).data


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ("id", "medicine", "dosage", "frequency", "duration", "instructions", "sort_order")
        read_only_fields = ("id",)


class ConsultationSerializer(serializers.ModelSerializer):
    patient = UserBriefSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        source="patient", queryset=_users_with_role(RoleCode.PATIENT), write_only=True
    )
    doctor = UserBriefSerializer(read_only=True)
    doctor_id = serializers.PrimaryKeyRelatedField(
        source="doctor",
        queryset=_users_with_role(RoleCode.DOCTOR),
        write_only=True,
        required=False,
    )
    doctor_specialization = serializers.SerializerMethodField()
    patient_profile_id = serializers.SerializerMethodField()
    patient_code = serializers.SerializerMethodField()
    prescription_items = PrescriptionItemSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = (
            "id",
            "patient",
            "patient_id",
            "patient_profile_id",
            "patient_code",
            "doctor",
            "doctor_id",
            "doctor_specialization",
            "scheduled_at",
            "mode",
            "status",
            "chief_complaint",
            "clinical_notes",
            "recommendations",
            "follow_up_date",
            "prescription_items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_doctor_specialization(self, obj):
        profile = getattr(obj.doctor, "doctor_profile", None)
        return profile.specialization if profile else None

    def get_patient_profile_id(self, obj):
        profile = getattr(obj.patient, "patient_profile", None)
        return str(profile.id) if profile else None

    def get_patient_code(self, obj):
        profile = getattr(obj.patient, "patient_profile", None)
        return profile.patient_code if profile else None


class BookingSerializer(serializers.Serializer):
    """A patient booking a consultation slot for themselves."""

    doctor_id = serializers.PrimaryKeyRelatedField(queryset=_users_with_role(RoleCode.DOCTOR))
    scheduled_at = serializers.DateTimeField()
    mode = serializers.ChoiceField(
        choices=ConsultationMode.choices, default=ConsultationMode.IN_PERSON
    )
    chief_complaint = serializers.CharField(max_length=1000, allow_blank=True, default="")

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Choose a time in the future.")
        return value


class PrescriptionUpdateSerializer(serializers.Serializer):
    items = PrescriptionItemSerializer(many=True)


class MedicalDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.full_name", read_only=True, default=None
    )
    patient_name = serializers.CharField(source="patient.user.full_name", read_only=True)
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = MedicalDocument
        fields = (
            "id",
            "patient",
            "patient_name",
            "title",
            "document_type",
            "file",
            "file_name",
            "file_size",
            "notes",
            "uploaded_by_name",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None

    def get_file_size(self, obj):
        try:
            return obj.file.size
        except (OSError, ValueError):
            return None


class VitalReadingSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(
        source="recorded_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = VitalReading
        fields = (
            "id",
            "patient",
            "recorded_at",
            "systolic_bp",
            "diastolic_bp",
            "heart_rate",
            "weight_kg",
            "sleep_hours",
            "notes",
            "recorded_by_name",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
