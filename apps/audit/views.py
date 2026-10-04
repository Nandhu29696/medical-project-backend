from rest_framework import permissions, viewsets

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from common.mixins import EnvelopeMixin
from common.permissions import IsAdmin


class AuditLogViewSet(EnvelopeMixin, viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/audit-logs/ — who did what, for Super Admin / Admin."""

    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filterset_fields = ["action", "entity_type", "actor"]
    search_fields = ["action", "entity_type", "entity_id", "actor__email"]
    ordering_fields = ["created_at"]
