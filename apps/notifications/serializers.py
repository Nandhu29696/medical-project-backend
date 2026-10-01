from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import (
    ContactPreference,
    MessageTemplate,
    Notification,
    NotificationChannel,
    NotificationLog,
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "category", "title", "message", "link", "is_read", "created_at")
        read_only_fields = fields


class MessageTemplateSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_display", read_only=True)
    updated_by_name = serializers.CharField(
        source="updated_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = MessageTemplate
        fields = (
            "id",
            "event",
            "event_label",
            "channel",
            "subject",
            "body",
            "is_active",
            "whatsapp_template_name",
            "whatsapp_params",
            "updated_by_name",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "event",
            "event_label",
            "channel",
            "updated_by_name",
            "updated_at",
        )

    def validate_whatsapp_params(self, value):
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise serializers.ValidationError(
                'Use a list of placeholder names, e.g. ["first_name"].'
            )
        return value


class NotificationLogSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(
        source="recipient.full_name", read_only=True, default=None
    )
    event_label = serializers.CharField(source="get_event_display", read_only=True)

    class Meta:
        model = NotificationLog
        fields = (
            "id",
            "recipient",
            "recipient_name",
            "channel",
            "event",
            "event_label",
            "to_address",
            "subject",
            "body",
            "status",
            "provider",
            "provider_message_id",
            "error",
            "sent_at",
            "created_at",
        )
        read_only_fields = fields


class TestMessageSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(
        choices=[NotificationChannel.EMAIL, NotificationChannel.WHATSAPP]
    )
    to = serializers.CharField(max_length=255)

    def validate(self, attrs):
        if attrs["channel"] == NotificationChannel.EMAIL:
            serializers.EmailField().run_validation(attrs["to"])
        return attrs


class ContactPreferenceSerializer(serializers.ModelSerializer):
    effective_whatsapp_number = serializers.SerializerMethodField()

    class Meta:
        model = ContactPreference
        fields = (
            "email_enabled",
            "whatsapp_enabled",
            "whatsapp_number",
            "whatsapp_opt_in_at",
            "reminders_enabled",
            "effective_whatsapp_number",
            "updated_at",
        )
        read_only_fields = ("whatsapp_opt_in_at", "effective_whatsapp_number", "updated_at")

    def get_effective_whatsapp_number(self, obj):
        return obj.whatsapp_number or obj.user.phone or ""

    def update(self, instance, validated_data):
        if validated_data.get("whatsapp_enabled") and not instance.whatsapp_enabled:
            instance.whatsapp_opt_in_at = timezone.now()
        if validated_data.get("whatsapp_enabled") is False:
            instance.whatsapp_opt_in_at = None
        return super().update(instance, validated_data)
