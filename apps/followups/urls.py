from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.followups.views import FollowUpViewSet

router = DefaultRouter()
router.register("followups", FollowUpViewSet, basename="followup")

urlpatterns = [
    path("", include(router.urls)),
]
