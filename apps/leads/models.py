from django.conf import settings
from django.db import models, transaction

from apps.campaigns.models import Campaign
from apps.products.models import Product
from common.models import TimeStampedUUIDModel


class LeadStatus(models.TextChoices):
    NEW = "NEW", "New"
    CONTACTED = "CONTACTED", "Contacted"
    INTERESTED = "INTERESTED", "Interested"
    FOLLOW_UP = "FOLLOW_UP", "Follow Up"
    CONVERTED = "CONVERTED", "Converted"
    NOT_INTERESTED = "NOT_INTERESTED", "Not Interested"
    NO_RESPONSE = "NO_RESPONSE", "No Response"
    INVALID = "INVALID", "Invalid"
    CLOSED = "CLOSED", "Closed"


class LeadPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class LeadNumberSequence(models.Model):
    """Single-row counter used to generate sequential, human-readable lead numbers
    (e.g. MED-000001) without using it as the database primary key."""

    value = models.PositiveIntegerField(default=0)


def generate_lead_number():
    with transaction.atomic():
        seq, _ = LeadNumberSequence.objects.select_for_update().get_or_create(pk=1)
        seq.value += 1
        seq.save(update_fields=["value"])
        return f"MED-{seq.value:06d}"


class Lead(TimeStampedUUIDModel):
    lead_number = models.CharField(max_length=20, unique=True, editable=False)

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=150, blank=True, null=True)
    state = models.CharField(max_length=150, blank=True, null=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    preferred_contact_method = models.CharField(max_length=32, blank=True, default="PHONE")
    message = models.TextField(blank=True, null=True)

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="leads")
    campaign = models.ForeignKey(
        Campaign, on_delete=models.SET_NULL, related_name="leads", null=True, blank=True
    )
    source = models.CharField(max_length=32, blank=True)
    medium = models.CharField(max_length=64, blank=True, null=True)
    campaign_name = models.CharField(max_length=255, blank=True, null=True)
    landing_page = models.URLField(max_length=500, blank=True, null=True)
    utm_source = models.CharField(max_length=128, blank=True, null=True)
    utm_medium = models.CharField(max_length=128, blank=True, null=True)
    utm_campaign = models.CharField(max_length=128, blank=True, null=True)
    utm_term = models.CharField(max_length=128, blank=True, null=True)
    utm_content = models.CharField(max_length=128, blank=True, null=True)

    status = models.CharField(max_length=32, choices=LeadStatus.choices, default=LeadStatus.NEW)
    priority = models.CharField(
        max_length=16, choices=LeadPriority.choices, default=LeadPriority.MEDIUM
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
        null=True,
        blank=True,
    )

    is_potential_duplicate = models.BooleanField(default=False)

    consent_given = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["status"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return self.lead_number or str(self.id)

    def save(self, *args, **kwargs):
        if not self.lead_number:
            self.lead_number = generate_lead_number()
        super().save(*args, **kwargs)


class LeadStatusHistory(TimeStampedUUIDModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=32, blank=True, null=True)
    new_status = models.CharField(max_length=32)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.TextField(blank=True, null=True)

    class Meta(TimeStampedUUIDModel.Meta):
        pass


class LeadNote(TimeStampedUUIDModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.TextField()
    is_deleted = models.BooleanField(default=False)

    class Meta(TimeStampedUUIDModel.Meta):
        pass
