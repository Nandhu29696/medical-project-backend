from django.contrib import admin

from apps.campaigns.models import Campaign


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "campaign_code", "status", "start_date", "end_date")
    list_filter = ("platform", "status")
    search_fields = ("name", "campaign_code")
