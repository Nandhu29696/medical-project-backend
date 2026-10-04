from django.contrib import admin

from apps.leads.models import Lead, LeadNote, LeadStatusHistory


class LeadNoteInline(admin.TabularInline):
    model = LeadNote
    extra = 0
    readonly_fields = ("created_by", "created_at")


class LeadStatusHistoryInline(admin.TabularInline):
    model = LeadStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "note", "created_at")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "lead_number",
        "first_name",
        "last_name",
        "phone",
        "status",
        "priority",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "priority", "source")
    search_fields = ("lead_number", "first_name", "last_name", "phone", "email")
    readonly_fields = ("lead_number",)
    inlines = [LeadStatusHistoryInline, LeadNoteInline]
