from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.clinical.views import (
    ClinicalSummaryView,
    ConsultationViewSet,
    DoctorViewSet,
    MedicalDocumentViewSet,
    PatientViewSet,
    PublicDoctorListView,
    VitalReadingViewSet,
)

router = DefaultRouter()
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("patients", PatientViewSet, basename="patient")
router.register("consultations", ConsultationViewSet, basename="consultation")
router.register("documents", MedicalDocumentViewSet, basename="document")
router.register("vitals", VitalReadingViewSet, basename="vital")

urlpatterns = [
    path("", include(router.urls)),
    path("clinical/summary/", ClinicalSummaryView.as_view(), name="clinical-summary"),
    path("public/doctors/", PublicDoctorListView.as_view(), name="public-doctor-list"),
]
