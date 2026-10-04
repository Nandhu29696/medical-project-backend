from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.media_files.views import serve_media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.accounts.management_urls")),
    path("api/v1/", include("apps.products.urls")),
    path("api/v1/", include("apps.leads.urls")),
    path("api/v1/", include("apps.followups.urls")),
    path("api/v1/", include("apps.campaigns.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.clinical.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.branding.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # Uploaded files, from the database (or disk), in every environment.
    path("media/<path:path>", serve_media, name="media"),
]
