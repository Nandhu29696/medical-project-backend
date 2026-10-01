from datetime import datetime, time, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import User
from apps.clinical.models import (
    Consultation,
    DoctorProfile,
    MedicalDocument,
    PatientProfile,
    VitalReading,
)
from apps.notifications.models import Notification
from common.demo_images import avatar_image


@pytest.fixture(autouse=True)
def media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def doctor_profile(doctor):
    return DoctorProfile.objects.create(
        user=doctor, specialization="Neurology", registration_number="REG-1"
    )


@pytest.fixture
def patient_profile(patient, doctor):
    return PatientProfile.objects.create(user=patient, assigned_doctor=doctor)


@pytest.fixture
def other_patient_profile(other_patient, other_doctor):
    return PatientProfile.objects.create(user=other_patient, assigned_doctor=other_doctor)


def _tomorrow_at(hour, minute=0):
    day = timezone.localdate() + timedelta(days=1)
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


# --- booking --------------------------------------------------------------------------------


@pytest.mark.django_db
def test_slots_listed_and_marked_taken(api_client, patient, doctor_profile, patient_profile):
    slot = _tomorrow_at(10)
    Consultation.objects.create(patient=patient, doctor=doctor_profile.user, scheduled_at=slot)
    api_client.force_authenticate(user=patient)
    response = api_client.get(
        f"/api/v1/doctors/{doctor_profile.id}/slots/?date={slot.date().isoformat()}"
    )
    assert response.status_code == 200
    slots = response.data["data"]["slots"]
    assert len(slots) == 14  # 10:00-17:00 every 30 minutes
    assert slots[0]["available"] is False
    assert slots[1]["available"] is True


@pytest.mark.django_db
def test_patient_books_slot_and_both_are_notified(
    api_client, patient, doctor, doctor_profile, patient_profile
):
    api_client.force_authenticate(user=patient)
    response = api_client.post(
        "/api/v1/consultations/book/",
        {
            "doctor_id": str(doctor.id),
            "scheduled_at": _tomorrow_at(11, 30).isoformat(),
            "mode": "VIDEO",
            "chief_complaint": "Test booking",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["data"]["patient"]["id"] == str(patient.id)
    assert Notification.objects.filter(recipient=doctor, category="CONSULTATION").exists()
    assert Notification.objects.filter(recipient=patient, category="CONSULTATION").exists()


@pytest.mark.django_db
def test_booking_rejects_taken_and_off_grid_slots(
    api_client, patient, other_patient, doctor, doctor_profile
):
    slot = _tomorrow_at(12)
    Consultation.objects.create(patient=other_patient, doctor=doctor, scheduled_at=slot)
    api_client.force_authenticate(user=patient)
    taken = api_client.post(
        "/api/v1/consultations/book/",
        {"doctor_id": str(doctor.id), "scheduled_at": slot.isoformat()},
        format="json",
    )
    assert taken.status_code == 400
    off_grid = api_client.post(
        "/api/v1/consultations/book/",
        {"doctor_id": str(doctor.id), "scheduled_at": _tomorrow_at(12, 10).isoformat()},
        format="json",
    )
    assert off_grid.status_code == 400
    evening = api_client.post(
        "/api/v1/consultations/book/",
        {"doctor_id": str(doctor.id), "scheduled_at": _tomorrow_at(19).isoformat()},
        format="json",
    )
    assert evening.status_code == 400


@pytest.mark.django_db
def test_only_patients_can_self_book(api_client, doctor, other_doctor):
    api_client.force_authenticate(user=doctor)
    response = api_client.post(
        "/api/v1/consultations/book/",
        {"doctor_id": str(other_doctor.id), "scheduled_at": _tomorrow_at(10).isoformat()},
        format="json",
    )
    assert response.status_code == 403


# --- prescriptions --------------------------------------------------------------------------


@pytest.mark.django_db
def test_doctor_writes_prescription_patient_reads_it(api_client, doctor, patient):
    consultation = Consultation.objects.create(
        patient=patient, doctor=doctor, scheduled_at=timezone.now()
    )
    api_client.force_authenticate(user=doctor)
    response = api_client.post(
        f"/api/v1/consultations/{consultation.id}/prescription/",
        {
            "items": [
                {"medicine": "Demo A", "dosage": "1 tab", "frequency": "OD"},
                {"medicine": "Demo B", "duration": "5 days"},
            ]
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    assert [i["medicine"] for i in response.data["data"]["prescription_items"]] == [
        "Demo A",
        "Demo B",
    ]
    assert Notification.objects.filter(recipient=patient, category="PRESCRIPTION").exists()

    api_client.force_authenticate(user=patient)
    detail = api_client.get(f"/api/v1/consultations/{consultation.id}/")
    assert len(detail.data["data"]["prescription_items"]) == 2
    denied = api_client.post(
        f"/api/v1/consultations/{consultation.id}/prescription/", {"items": []}, format="json"
    )
    assert denied.status_code == 403


@pytest.mark.django_db
def test_other_doctor_cannot_prescribe(api_client, doctor, other_doctor, patient):
    consultation = Consultation.objects.create(
        patient=patient, doctor=doctor, scheduled_at=timezone.now()
    )
    api_client.force_authenticate(user=other_doctor)
    response = api_client.post(
        f"/api/v1/consultations/{consultation.id}/prescription/", {"items": []}, format="json"
    )
    assert response.status_code == 404


# --- documents & vitals ---------------------------------------------------------------------


def _pdf():
    return SimpleUploadedFile("report.pdf", b"%PDF-1.4 demo", content_type="application/pdf")


@pytest.mark.django_db
def test_patient_uploads_own_document_doctor_sees_it(
    api_client, patient, doctor, patient_profile, other_patient_profile
):
    api_client.force_authenticate(user=patient)
    response = api_client.post(
        "/api/v1/documents/",
        {"patient": str(patient_profile.id), "title": "My report", "file": _pdf()},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert Notification.objects.filter(recipient=doctor, category="DOCUMENT").exists()

    forbidden = api_client.post(
        "/api/v1/documents/",
        {"patient": str(other_patient_profile.id), "title": "Not mine", "file": _pdf()},
        format="multipart",
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(user=doctor)
    listing = api_client.get("/api/v1/documents/")
    assert listing.data["data"]["count"] == 1


@pytest.mark.django_db
def test_documents_are_scoped(api_client, other_doctor, patient_profile, doctor):
    MedicalDocument.objects.create(patient=patient_profile, title="x", file=_pdf())
    api_client.force_authenticate(user=other_doctor)
    assert api_client.get("/api/v1/documents/").data["data"]["count"] == 0


@pytest.mark.django_db
def test_vitals_recorded_and_scoped(api_client, patient, doctor, other_doctor, patient_profile):
    api_client.force_authenticate(user=doctor)
    response = api_client.post(
        "/api/v1/vitals/",
        {
            "patient": str(patient_profile.id),
            "recorded_at": timezone.now().isoformat(),
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "weight_kg": "70.5",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert VitalReading.objects.get().recorded_by == doctor
    api_client.force_authenticate(user=patient)
    assert api_client.get("/api/v1/vitals/").data["data"]["count"] == 1
    api_client.force_authenticate(user=other_doctor)
    assert api_client.get("/api/v1/vitals/").data["data"]["count"] == 0


@pytest.mark.django_db
def test_patient_uploads_own_photo(api_client, patient, patient_profile):
    api_client.force_authenticate(user=patient)
    photo = avatar_image("PT", (10, 10, 10), "me.png")
    upload = SimpleUploadedFile("me.png", photo.read(), content_type="image/png")
    response = api_client.post("/api/v1/patients/me/photo/", {"photo": upload}, format="multipart")
    assert response.status_code == 200, response.data
    patient_profile.refresh_from_db()
    assert patient_profile.photo


@pytest.mark.django_db
def test_doctor_updates_own_profile(api_client, doctor, doctor_profile):
    api_client.force_authenticate(user=doctor)
    response = api_client.patch(
        "/api/v1/doctors/me/", {"bio": "Updated", "is_available": False}, format="json"
    )
    assert response.status_code == 200
    doctor_profile.refresh_from_db()
    assert doctor_profile.bio == "Updated" and doctor_profile.is_available is False


# --- accounts -------------------------------------------------------------------------------


@pytest.mark.django_db
def test_patient_self_registration(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {
            "email": "new.patient@test.demo",
            "password": "Strong!Pass42",
            "first_name": "New",
            "last_name": "Patient",
            "consent_given": True,
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    user = User.objects.get(email="new.patient@test.demo")
    assert user.role_codes == ["PATIENT"]
    assert PatientProfile.objects.filter(user=user).exists()
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": "new.patient@test.demo", "password": "Strong!Pass42"},
        format="json",
    )
    assert login.status_code == 200


@pytest.mark.django_db
def test_registration_rejects_weak_password_duplicate_email_and_missing_consent(
    api_client, patient
):
    base = {"first_name": "A", "consent_given": True}
    weak = api_client.post(
        "/api/v1/auth/register/",
        {**base, "email": "a@test.demo", "password": "12345678"},
        format="json",
    )
    assert weak.status_code == 400
    duplicate = api_client.post(
        "/api/v1/auth/register/",
        {**base, "email": "patient@test.demo", "password": "Strong!Pass42"},
        format="json",
    )
    assert duplicate.status_code == 400
    no_consent = api_client.post(
        "/api/v1/auth/register/",
        {**base, "email": "b@test.demo", "password": "Strong!Pass42", "consent_given": False},
        format="json",
    )
    assert no_consent.status_code == 400


@pytest.mark.django_db
def test_change_password(api_client, doctor):
    api_client.force_authenticate(user=doctor)
    wrong = api_client.post(
        "/api/v1/auth/change-password/",
        {"current_password": "nope", "new_password": "Another!Pass42"},
        format="json",
    )
    assert wrong.status_code == 400
    ok = api_client.post(
        "/api/v1/auth/change-password/",
        {"current_password": "TestPass123!", "new_password": "Another!Pass42"},
        format="json",
    )
    assert ok.status_code == 200
    doctor.refresh_from_db()
    assert doctor.check_password("Another!Pass42")


@pytest.mark.django_db
def test_update_own_profile(api_client, patient):
    api_client.force_authenticate(user=patient)
    response = api_client.patch(
        "/api/v1/auth/me/", {"first_name": "Renamed", "phone": "999"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["data"]["first_name"] == "Renamed"


@pytest.mark.django_db
def test_assignable_users_for_managers_only(api_client, sales_manager, sales_executive, doctor):
    api_client.force_authenticate(user=sales_manager)
    response = api_client.get("/api/v1/users/assignable/")
    assert response.status_code == 200
    emails = {u["email"] for u in response.data["data"]}
    assert emails == {"manager@test.demo", "exec@test.demo"}
    api_client.force_authenticate(user=sales_executive)
    assert api_client.get("/api/v1/users/assignable/").status_code == 403


# --- notifications, audit, public ------------------------------------------------------------


@pytest.mark.django_db
def test_notifications_are_private_and_markable(api_client, patient, doctor):
    Notification.objects.create(recipient=patient, title="Mine")
    Notification.objects.create(recipient=doctor, title="Not mine")
    api_client.force_authenticate(user=patient)
    listing = api_client.get("/api/v1/notifications/")
    assert [n["title"] for n in listing.data["data"]["results"]] == ["Mine"]
    assert api_client.get("/api/v1/notifications/unread-count/").data["data"]["count"] == 1
    api_client.post("/api/v1/notifications/read-all/")
    assert api_client.get("/api/v1/notifications/unread-count/").data["data"]["count"] == 0


@pytest.mark.django_db
def test_lead_assignment_creates_in_app_notification(
    api_client, sales_manager, sales_executive, product
):
    from apps.leads.models import Lead

    lead = Lead.objects.create(first_name="A", phone="9000000000", product=product)
    api_client.force_authenticate(user=sales_manager)
    api_client.post(
        f"/api/v1/leads/{lead.id}/assign/", {"assigned_to": str(sales_executive.id)}, format="json"
    )
    assert Notification.objects.filter(recipient=sales_executive, category="LEAD").exists()


@pytest.mark.django_db
def test_audit_log_admin_only(api_client, admin_user, doctor):
    api_client.force_authenticate(user=doctor)
    api_client.patch("/api/v1/auth/me/", {"phone": "1"}, format="json")
    assert api_client.get("/api/v1/audit-logs/").status_code == 403
    api_client.force_authenticate(user=admin_user)
    assert api_client.get("/api/v1/audit-logs/").status_code == 200


@pytest.mark.django_db
def test_public_doctors_hide_private_fields(api_client, doctor_profile):
    response = api_client.get("/api/v1/public/doctors/")
    assert response.status_code == 200
    row = response.data[0]
    assert row["specialization"] == "Neurology"
    assert "registration_number" not in row and "email" not in str(row)


@pytest.mark.django_db
def test_clinical_summary_has_today_and_follow_ups(api_client, doctor, patient, patient_profile):
    Consultation.objects.create(
        patient=patient,
        doctor=doctor,
        scheduled_at=timezone.now(),
        status="COMPLETED",
        follow_up_date=timezone.localdate() + timedelta(days=2),
    )
    api_client.force_authenticate(user=doctor)
    data = api_client.get("/api/v1/clinical/summary/").data["data"]
    assert data["today_consultations"] == 1
    assert data["follow_ups_due"] == 1


@pytest.mark.django_db
def test_consultation_date_filters(api_client, admin_user, doctor, patient):
    Consultation.objects.create(patient=patient, doctor=doctor, scheduled_at=_tomorrow_at(10))
    Consultation.objects.create(
        patient=patient, doctor=doctor, scheduled_at=_tomorrow_at(10) + timedelta(days=10)
    )
    api_client.force_authenticate(user=admin_user)
    after = _tomorrow_at(0).isoformat()
    before = (_tomorrow_at(0) + timedelta(days=1)).isoformat()
    response = api_client.get(
        "/api/v1/consultations/", {"scheduled_after": after, "scheduled_before": before}
    )
    assert response.data["data"]["count"] == 1
