import secrets

from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


def generate_patient_code():
    return f"PAT-{secrets.token_hex(4).upper()}"


class Gender(models.TextChoices):
    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    OTHER = "OTHER", "Other"
    UNDISCLOSED = "UNDISCLOSED", "Prefer not to say"


class BloodGroup(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"
    UNKNOWN = "UNKNOWN", "Unknown"


class DoctorProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile"
    )
    specialization = models.CharField(max_length=150)
    qualification = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=64, unique=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    clinic_name = models.CharField(max_length=255, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="doctors/%Y/%m/", blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.user.full_name} ({self.specialization})"


class PatientProfile(TimeStampedUUIDModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile"
    )
    patient_code = models.CharField(
        max_length=20, unique=True, default=generate_patient_code, editable=False
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=Gender.choices, default=Gender.UNDISCLOSED)
    blood_group = models.CharField(
        max_length=8, choices=BloodGroup.choices, default=BloodGroup.UNKNOWN
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=150, blank=True)
    state = models.CharField(max_length=150, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    medical_history = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    photo = models.ImageField(upload_to="patients/%Y/%m/", blank=True)
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_patients",
        null=True,
        blank=True,
    )
    source_lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        related_name="patient_profiles",
        null=True,
        blank=True,
        help_text="The website enquiry this patient originated from, if any.",
    )

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [models.Index(fields=["patient_code"])]

    def __str__(self):
        return f"{self.patient_code} — {self.user.full_name}"


class ConsultationStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    NO_SHOW = "NO_SHOW", "No Show"


class ConsultationMode(models.TextChoices):
    IN_PERSON = "IN_PERSON", "In person"
    VIDEO = "VIDEO", "Video"
    PHONE = "PHONE", "Phone"


class Consultation(TimeStampedUUIDModel):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_consultations"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="doctor_consultations"
    )
    scheduled_at = models.DateTimeField()
    mode = models.CharField(
        max_length=16, choices=ConsultationMode.choices, default=ConsultationMode.IN_PERSON
    )
    status = models.CharField(
        max_length=16, choices=ConsultationStatus.choices, default=ConsultationStatus.SCHEDULED
    )
    chief_complaint = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta(TimeStampedUUIDModel.Meta):
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["doctor", "scheduled_at"]),
            models.Index(fields=["patient", "scheduled_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.patient} with {self.doctor} at {self.scheduled_at:%Y-%m-%d %H:%M}"


class PrescriptionItem(TimeStampedUUIDModel):
    """One medicine line on a consultation's prescription."""

    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name="prescription_items"
    )
    medicine = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    instructions = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(TimeStampedUUIDModel.Meta):
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.medicine} ({self.dosage})"


class DocumentType(models.TextChoices):
    LAB_REPORT = "LAB_REPORT", "Lab report"
    SCAN = "SCAN", "Scan / imaging"
    PRESCRIPTION = "PRESCRIPTION", "Prescription"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY", "Discharge summary"
    OTHER = "OTHER", "Other"


class MedicalDocument(TimeStampedUUIDModel):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=24, choices=DocumentType.choices, default=DocumentType.OTHER
    )
    file = models.FileField(upload_to="documents/%Y/%m/")
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title


class VitalReading(TimeStampedUUIDModel):
    """A dated set of health measurements; every value is optional."""

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="vitals")
    recorded_at = models.DateTimeField()
    systolic_bp = models.PositiveSmallIntegerField(null=True, blank=True)
    diastolic_bp = models.PositiveSmallIntegerField(null=True, blank=True)
    heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta(TimeStampedUUIDModel.Meta):
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["patient", "recorded_at"])]
