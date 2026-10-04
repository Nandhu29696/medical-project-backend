from django.conf import settings
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.notifications.defaults import DEFAULT_TEMPLATES
from apps.notifications.models import (
    MessageEvent,
    MessageTemplate,
    Notification,
    NotificationChannel,
    NotificationLog,
)
from apps.notifications.providers import email_mode, whatsapp_configured
from apps.notifications.serializers import (
    ContactPreferenceSerializer,
    MessageTemplateSerializer,
    NotificationLogSerializer,
    NotificationSerializer,
    TestMessageSerializer,
)
from apps.notifications.services import (
    dispatch,
    ensure_default_templates,
    normalize_whatsapp_number,
    preferences_for,
    send_due_reminders,
)
from common.mixins import EnvelopeMixin
from common.permissions import IsAdmin, IsSuperAdmin
from common.responses import success_response


class NotificationViewSet(EnvelopeMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """The signed-in user's own in-app notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["is_read", "category"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return success_response({"count": self.get_queryset().filter(is_read=False).count()})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        return success_response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return success_response({"updated": updated}, message="All notifications marked as read.")


class ContactPreferenceView(APIView):
    """GET/PATCH /api/v1/me/contact-preferences/ — how I want to be contacted."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return success_response(ContactPreferenceSerializer(preferences_for(request.user)).data)

    def patch(self, request):
        prefs = preferences_for(request.user)
        serializer = ContactPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        number = serializer.validated_data.get("whatsapp_number")
        if number and not normalize_whatsapp_number(number):
            raise ValidationError({"whatsapp_number": ["Enter a valid mobile number."]})
        serializer.save()
        log_action(
            actor=request.user,
            action="CONTACT_PREFERENCES_UPDATED",
            entity_type="ContactPreference",
            entity_id=request.user.id,
            new_values={
                k: v for k, v in serializer.validated_data.items() if k != "whatsapp_number"
            },
            request=request,
        )
        return success_response(serializer.data, message="Preferences saved.")


class MessagingStatusView(APIView):
    """GET /api/v1/messaging/status/ — which channels are live (no secrets returned)."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        mode = email_mode()
        phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
        return success_response(
            {
                "email": {
                    "mode": mode,
                    "live": mode == "smtp",
                    "host": settings.EMAIL_HOST if mode == "smtp" else None,
                    "from_address": settings.DEFAULT_FROM_EMAIL,
                    "file_path": settings.EMAIL_FILE_PATH if mode == "file" else None,
                },
                "whatsapp": {
                    "provider": settings.WHATSAPP_PROVIDER,
                    "live": settings.WHATSAPP_PROVIDER == "meta" and whatsapp_configured(),
                    "configured": whatsapp_configured(),
                    "phone_number_id": f"…{phone_id[-4:]}" if phone_id else None,
                    "test_recipients": len(settings.WHATSAPP_TEST_RECIPIENTS),
                },
                "delivery": settings.NOTIFICATIONS_DELIVERY,
                "reminder_hours_before": settings.REMINDER_HOURS_BEFORE,
                "skip_domains": settings.NOTIFICATIONS_SKIP_DOMAINS,
                "frontend_url": settings.FRONTEND_URL,
            }
        )


class MessageTemplateViewSet(
    EnvelopeMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Editable email / WhatsApp wording per event. Super Admin only."""

    serializer_class = MessageTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    pagination_class = None
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        ensure_default_templates()
        return MessageTemplate.objects.select_related("updated_by")

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        log_action(
            actor=self.request.user,
            action="MESSAGE_TEMPLATE_UPDATED",
            entity_type="MessageTemplate",
            entity_id=instance.id,
            new_values={
                "event": instance.event,
                "channel": instance.channel,
                "is_active": instance.is_active,
            },
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def reset(self, request, pk=None):
        template = self.get_object()
        defaults = DEFAULT_TEMPLATES.get((template.event, template.channel), {})
        template.subject = defaults.get("subject", "")
        template.body = defaults.get("body", template.body)
        template.whatsapp_params = defaults.get("whatsapp_params", [])
        template.whatsapp_template_name = ""
        template.is_active = defaults.get("is_active", True)
        template.updated_by = request.user
        template.save()
        return success_response(MessageTemplateSerializer(template).data, message="Template reset.")


class NotificationLogViewSet(EnvelopeMixin, viewsets.ReadOnlyModelViewSet):
    """Delivery log for every email / WhatsApp message (Super Admin / Admin)."""

    queryset = NotificationLog.objects.select_related("recipient")
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filterset_fields = ["status", "channel", "event"]
    search_fields = ["to_address", "subject", "recipient__email"]
    ordering_fields = ["created_at"]


class TestMessageView(APIView):
    """POST /api/v1/messaging/test/ {"channel": "EMAIL"|"WHATSAPP", "to": "..."} — sends now."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = TestMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel, to = serializer.validated_data["channel"], serializer.validated_data["to"]
        logs = dispatch(
            MessageEvent.TEST,
            email=to if channel == NotificationChannel.EMAIL else None,
            phone=to if channel == NotificationChannel.WHATSAPP else None,
            context={"full_name": request.user.full_name},
            deliver_now=True,
        )
        if not logs:
            raise ValidationError(
                {"channel": ["The test template for this channel is turned off."]}
            )
        log = NotificationLog.objects.get(pk=logs[0].pk)
        return success_response(
            NotificationLogSerializer(log).data, message=f"Test {log.status.lower()}."
        )


class RunRemindersView(APIView):
    """POST /api/v1/messaging/reminders/run/ — send any due reminders right now."""

    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        count = send_due_reminders()
        return success_response({"sent": count}, message=f"{count} reminder(s) sent.")
