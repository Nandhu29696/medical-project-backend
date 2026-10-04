from django.conf import settings
from django.db import models

from common.models import TimeStampedUUIDModel


class AuditLog(TimeStampedUUIDModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64, blank=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}:{self.entity_id}"
