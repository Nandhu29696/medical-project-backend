from django.contrib import admin

from apps.followups.models import FollowUp


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("lead", "assigned_to", "scheduled_at", "status", "completed_at")
    list_filter = ("status",)
