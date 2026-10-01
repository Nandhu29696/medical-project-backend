from rest_framework import permissions, viewsets

from apps.audit.services import log_action
from apps.campaigns.models import Campaign
from apps.campaigns.serializers import CampaignSerializer
from common.mixins import EnvelopeMixin
from common.permissions import IsCrmUser, IsSalesManagerOrAbove


class CampaignViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    filterset_fields = ["platform", "status"]
    search_fields = ["name", "campaign_code"]
    ordering_fields = ["created_at", "start_date"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsSalesManagerOrAbove()]
        return [permissions.IsAuthenticated(), IsCrmUser()]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="CAMPAIGN_CREATED",
            entity_type="Campaign",
            entity_id=instance.id,
            new_values=serializer.data,
            request=self.request,
        )

    def perform_update(self, serializer):
        old_values = CampaignSerializer(self.get_object()).data
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="CAMPAIGN_UPDATED",
            entity_type="Campaign",
            entity_id=instance.id,
            old_values=old_values,
            new_values=serializer.data,
            request=self.request,
        )
