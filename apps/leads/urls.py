from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.leads.views import LeadViewSet, PublicLeadCreateView

router = DefaultRouter()
router.register("leads", LeadViewSet, basename="lead")

urlpatterns = [
    path("public/leads/", PublicLeadCreateView.as_view(), name="public-lead-create"),
    path("", include(router.urls)),
]
