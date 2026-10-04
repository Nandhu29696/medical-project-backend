from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "actor_name",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "old_values",
            "new_values",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
