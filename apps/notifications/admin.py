from django.contrib import admin

from apps.notifications.models import (
    ContactPreference,
    MessageTemplate,
    Notification,
    NotificationLog,
)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "event", "to_address", "status", "provider")
    list_filter = ("channel", "status", "event")
    search_fields = ("to_address", "subject")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "category", "title", "is_read", "created_at")
    list_filter = ("category", "is_read")


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("event", "channel", "is_active", "whatsapp_template_name", "updated_at")
    list_filter = ("channel", "is_active")


@admin.register(ContactPreference)
class ContactPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_enabled", "whatsapp_enabled", "reminders_enabled", "updated_at")
