from rest_framework import serializers

from apps.followups.models import FollowUp


class FollowUpSerializer(serializers.ModelSerializer):
    lead_number = serializers.CharField(source="lead.lead_number", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=None
    )

    class Meta:
        model = FollowUp
        fields = (
            "id",
            "lead",
            "lead_number",
            "assigned_to",
            "assigned_to_name",
            "scheduled_at",
            "completed_at",
            "outcome",
            "notes",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "completed_at", "created_at", "updated_at")


class FollowUpCompleteSerializer(serializers.Serializer):
    outcome = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
