from django.db import models

from common.models import TimeStampedUUIDModel


class CampaignPlatform(models.TextChoices):
    META = "META", "Meta"
    GOOGLE = "GOOGLE", "Google"
    INSTAGRAM = "INSTAGRAM", "Instagram"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    YOUTUBE = "YOUTUBE", "YouTube"
    ORGANIC = "ORGANIC", "Organic"
    REFERRAL = "REFERRAL", "Referral"
    QR = "QR", "QR"
    OTHER = "OTHER", "Other"


class CampaignStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    ENDED = "ENDED", "Ended"


class Campaign(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=16, choices=CampaignPlatform.choices)
    campaign_code = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=CampaignStatus.choices, default=CampaignStatus.ACTIVE
    )

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [models.Index(fields=["campaign_code"])]

    def __str__(self):
        return self.name
