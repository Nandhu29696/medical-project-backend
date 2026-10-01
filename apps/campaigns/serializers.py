from rest_framework import serializers

from apps.campaigns.models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "platform",
            "campaign_code",
            "description",
            "start_date",
            "end_date",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
