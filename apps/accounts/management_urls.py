from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import AssignableUsersView, RoleViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")

urlpatterns = [
    # Must come before the router so "assignable" is not treated as a user id.
    path("users/assignable/", AssignableUsersView.as_view(), name="users-assignable"),
    path("", include(router.urls)),
]
