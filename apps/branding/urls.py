from django.urls import path

from apps.branding.views import PublicThemeView, ThemeAdminView

urlpatterns = [
    path("public/theme/", PublicThemeView.as_view(), name="public-theme"),
    path("theme/", ThemeAdminView.as_view(), name="theme-admin"),
]
