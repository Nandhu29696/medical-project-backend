from django.contrib import admin

from apps.clinical.models import Consultation, DoctorProfile, PatientProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "registration_number",
        "years_of_experience",
        "is_available",
    )
    list_filter = ("specialization", "is_available")
    search_fields = ("user__email", "user__first_name", "user__last_name", "registration_number")
    raw_id_fields = ("user",)


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("patient_code", "user", "gender", "blood_group", "assigned_doctor", "city")
    list_filter = ("gender", "blood_group")
    search_fields = ("patient_code", "user__email", "user__first_name", "user__last_name")
    raw_id_fields = ("user", "assigned_doctor", "source_lead")


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "scheduled_at", "mode", "status")
    list_filter = ("status", "mode")
    search_fields = ("patient__email", "doctor__email")
    raw_id_fields = ("patient", "doctor", "created_by")
