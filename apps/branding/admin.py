from django.contrib import admin

from apps.branding.models import SiteTheme


@admin.register(SiteTheme)
class SiteThemeAdmin(admin.ModelAdmin):
    list_display = ("preset", "primary_color", "accent_color", "heading_font", "updated_at")
