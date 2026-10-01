from django.conf import settings
from django.db import models

from apps.leads.models import Lead
from common.models import TimeStampedUUIDModel


class FollowUpStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    MISSED = "MISSED", "Missed"
    CANCELLED = "CANCELLED", "Cancelled"


class FollowUp(TimeStampedUUIDModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="followups")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="followups",
        null=True,
        blank=True,
    )
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=16, choices=FollowUpStatus.choices, default=FollowUpStatus.PENDING
    )

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [models.Index(fields=["scheduled_at"])]

    def __str__(self):
        return f"Follow-up for {self.lead.lead_number} at {self.scheduled_at}"
