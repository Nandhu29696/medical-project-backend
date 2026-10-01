from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class NotificationChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    SMS = "SMS", "SMS"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class MessageEvent(models.TextChoices):
    """Things that can trigger an email / WhatsApp message."""

    WELCOME = "WELCOME", "Welcome (new patient account)"
    ENQUIRY_RECEIVED = "ENQUIRY_RECEIVED", "Enquiry received"
    CONSULTATION_BOOKED = "CONSULTATION_BOOKED", "Consultation booked / scheduled"
    CONSULTATION_REMINDER = "CONSULTATION_REMINDER", "Consultation reminder"
    CONSULTATION_CANCELLED = "CONSULTATION_CANCELLED", "Consultation cancelled"
    PRESCRIPTION_READY = "PRESCRIPTION_READY", "Prescription ready"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "New report / document"
    DOCTOR_NEW_BOOKING = "DOCTOR_NEW_BOOKING", "Doctor: new booking"
    LEAD_ASSIGNED = "LEAD_ASSIGNED", "Sales: lead assigned"
    TEST = "TEST", "Test message"


class NotificationLog(TimeStampedUUIDModel):
    """Every outbound email / WhatsApp message and what happened to it."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    event = models.CharField(max_length=32, choices=MessageEvent.choices, blank=True)
    to_address = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=NotificationStatus.choices, default=NotificationStatus.PENDING
    )
    provider = models.CharField(max_length=32, blank=True)
    provider_message_id = models.CharField(max_length=128, blank=True)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [models.Index(fields=["status", "channel"]), models.Index(fields=["event"])]

    def __str__(self):
        return f"{self.channel} {self.event} -> {self.to_address} ({self.status})"


class MessageTemplate(TimeStampedUUIDModel):
    """
    Editable text for each event and channel. `{placeholders}` are filled from the event
    context. For WhatsApp's Cloud API, business-initiated messages must use a template that
    Meta has approved: put its name in `whatsapp_template_name` and list, in order, the
    placeholders that fill its {{1}}, {{2}}… variables in `whatsapp_params`.
    """

    event = models.CharField(max_length=32, choices=MessageEvent.choices)
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    whatsapp_template_name = models.CharField(max_length=128, blank=True)
    whatsapp_params = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta(TimeStampedUUIDModel.Meta):
        ordering = ["event", "channel"]
        constraints = [
            models.UniqueConstraint(fields=["event", "channel"], name="unique_event_channel")
        ]

    def __str__(self):
        return f"{self.event} / {self.channel}"


class ContactPreference(models.Model):
    """How a person agrees to be contacted outside the app."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contact_preference"
    )
    email_enabled = models.BooleanField(default=True)
    # WhatsApp needs explicit opt-in (WhatsApp Business policy and consent rules).
    whatsapp_enabled = models.BooleanField(default=False)
    whatsapp_number = models.CharField(
        max_length=20, blank=True, help_text="Leave empty to use the phone number on the account."
    )
    whatsapp_opt_in_at = models.DateTimeField(null=True, blank=True)
    reminders_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contact_preferences"

    def __str__(self):
        return f"Contact preferences for {self.user_id}"


class NotificationCategory(models.TextChoices):
    LEAD = "LEAD", "Lead"
    CONSULTATION = "CONSULTATION", "Consultation"
    PRESCRIPTION = "PRESCRIPTION", "Prescription"
    DOCUMENT = "DOCUMENT", "Document"
    ACCOUNT = "ACCOUNT", "Account"
    SYSTEM = "SYSTEM", "System"


class Notification(TimeStampedUUIDModel):
    """In-app notification shown in the bell menu."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    category = models.CharField(
        max_length=16, choices=NotificationCategory.choices, default=NotificationCategory.SYSTEM
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient_id}: {self.title}"
