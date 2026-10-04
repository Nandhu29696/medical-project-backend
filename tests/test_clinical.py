from datetime import timedelta

import pytest
from django.utils import timezone

from apps.clinical.models import Consultation, ConsultationStatus, DoctorProfile, PatientProfile


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


@pytest.fixture
def consultation(patient, doctor):
    return Consultation.objects.create(
        patient=patient, doctor=doctor, scheduled_at=timezone.now() + timedelta(days=1)
    )


@pytest.fixture
def other_consultation(other_patient, other_doctor):
    return Consultation.objects.create(
        patient=other_patient,
        doctor=other_doctor,
        scheduled_at=timezone.now() + timedelta(days=2),
    )


def _ids(response):
    return {row["id"] for row in response.data["data"]["results"]}


@pytest.mark.django_db
def test_patient_code_generated(patient_profile):
    assert patient_profile.patient_code.startswith("PAT-")


@pytest.mark.django_db
def test_admin_sees_all_patients(api_client, admin_user, patient_profile, other_patient_profile):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get("/api/v1/patients/")
    assert response.status_code == 200
    assert _ids(response) == {str(patient_profile.id), str(other_patient_profile.id)}


@pytest.mark.django_db
def test_doctor_sees_only_own_patients(api_client, doctor, patient_profile, other_patient_profile):
    api_client.force_authenticate(user=doctor)
    response = api_client.get("/api/v1/patients/")
    assert _ids(response) == {str(patient_profile.id)}
    assert api_client.get(f"/api/v1/patients/{other_patient_profile.id}/").status_code == 404


@pytest.mark.django_db
def test_patient_sees_only_self(api_client, patient, patient_profile, other_patient_profile):
    api_client.force_authenticate(user=patient)
    response = api_client.get("/api/v1/patients/")
    assert _ids(response) == {str(patient_profile.id)}
    me = api_client.get("/api/v1/patients/me/")
    assert me.status_code == 200
    assert me.data["data"]["patient_code"] == patient_profile.patient_code


@pytest.mark.django_db
def test_sales_staff_see_no_patients(api_client, sales_executive, patient_profile):
    api_client.force_authenticate(user=sales_executive)
    assert _ids(api_client.get("/api/v1/patients/")) == set()


@pytest.mark.django_db
def test_patient_cannot_edit_own_record(api_client, patient, patient_profile):
    api_client.force_authenticate(user=patient)
    response = api_client.patch(
        f"/api/v1/patients/{patient_profile.id}/", {"allergies": "x"}, format="json"
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_assigned_doctor_can_edit_clinical_fields_only(
    api_client, doctor, patient_profile, other_doctor
):
    api_client.force_authenticate(user=doctor)
    response = api_client.patch(
        f"/api/v1/patients/{patient_profile.id}/",
        {"allergies": "Peanuts (test)", "assigned_doctor_id": str(other_doctor.id)},
        format="json",
    )
    assert response.status_code == 200
    patient_profile.refresh_from_db()
    assert patient_profile.allergies == "Peanuts (test)"
    assert patient_profile.assigned_doctor_id == doctor.id


@pytest.mark.django_db
def test_admin_creates_patient_profile(api_client, admin_user, patient, doctor):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/v1/patients/",
        {"user_id": str(patient.id), "assigned_doctor_id": str(doctor.id), "gender": "FEMALE"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["data"]["assigned_doctor"]["email"] == "doctor@test.demo"
    # A second profile for the same user is rejected.
    again = api_client.post("/api/v1/patients/", {"user_id": str(patient.id)}, format="json")
    assert again.status_code == 400


@pytest.mark.django_db
def test_patient_profile_requires_patient_role(api_client, admin_user, doctor):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post("/api/v1/patients/", {"user_id": str(doctor.id)}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_consultation_visibility(
    api_client, doctor, patient, admin_user, consultation, other_consultation
):
    api_client.force_authenticate(user=doctor)
    assert _ids(api_client.get("/api/v1/consultations/")) == {str(consultation.id)}
    api_client.force_authenticate(user=patient)
    assert _ids(api_client.get("/api/v1/consultations/")) == {str(consultation.id)}
    api_client.force_authenticate(user=admin_user)
    assert len(_ids(api_client.get("/api/v1/consultations/"))) == 2


@pytest.mark.django_db
def test_doctor_books_consultation_for_self(api_client, doctor, other_doctor, patient):
    api_client.force_authenticate(user=doctor)
    response = api_client.post(
        "/api/v1/consultations/",
        {
            "patient_id": str(patient.id),
            "doctor_id": str(other_doctor.id),
            "scheduled_at": (timezone.now() + timedelta(days=3)).isoformat(),
            "chief_complaint": "Test",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["data"]["doctor"]["id"] == str(doctor.id)


@pytest.mark.django_db
def test_admin_must_choose_doctor(api_client, admin_user, patient):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/v1/consultations/",
        {"patient_id": str(patient.id), "scheduled_at": timezone.now().isoformat()},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_patient_cannot_create_consultation(api_client, patient, doctor):
    api_client.force_authenticate(user=patient)
    response = api_client.post(
        "/api/v1/consultations/",
        {
            "patient_id": str(patient.id),
            "doctor_id": str(doctor.id),
            "scheduled_at": timezone.now().isoformat(),
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_doctor_completes_own_consultation(api_client, doctor, consultation):
    api_client.force_authenticate(user=doctor)
    response = api_client.patch(
        f"/api/v1/consultations/{consultation.id}/",
        {"status": "COMPLETED", "clinical_notes": "Seen (test)."},
        format="json",
    )
    assert response.status_code == 200
    consultation.refresh_from_db()
    assert consultation.status == ConsultationStatus.COMPLETED


@pytest.mark.django_db
def test_doctor_cannot_touch_other_doctors_consultation(api_client, doctor, other_consultation):
    api_client.force_authenticate(user=doctor)
    response = api_client.patch(
        f"/api/v1/consultations/{other_consultation.id}/", {"status": "CANCELLED"}, format="json"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_doctor_directory_readable_by_patient_but_not_writable(api_client, patient, doctor_profile):
    api_client.force_authenticate(user=patient)
    response = api_client.get("/api/v1/doctors/")
    assert response.status_code == 200
    assert _ids(response) == {str(doctor_profile.id)}
    assert (
        api_client.patch(
            f"/api/v1/doctors/{doctor_profile.id}/", {"bio": "x"}, format="json"
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_clinical_summary_is_scoped(
    api_client, doctor, patient_profile, other_patient_profile, consultation, other_consultation
):
    api_client.force_authenticate(user=doctor)
    data = api_client.get("/api/v1/clinical/summary/").data["data"]
    assert data["patients"] == 1
    assert data["upcoming_consultations"] == 1
