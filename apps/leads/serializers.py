import re

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.campaigns.models import Campaign
from apps.leads.models import Lead, LeadNote, LeadStatusHistory
from apps.products.models import Product

PHONE_REGEX = re.compile(r"^[0-9+\-\s()]{7,20}$")


class PublicLeadCreateSerializer(serializers.ModelSerializer):
    """Serializer for the internet-facing public enquiry endpoint.

    Includes a honeypot field: real users never see/fill it, bots that
    auto-fill every input will, so we silently reject submissions that set it.
    """

    product_id = serializers.PrimaryKeyRelatedField(
        source="product", queryset=Product.objects.all(), write_only=True
    )
    campaign_id = serializers.PrimaryKeyRelatedField(
        source="campaign",
        queryset=Campaign.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    consent_given = serializers.BooleanField(write_only=True)
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Lead
        fields = (
            "first_name",
            "last_name",
            "phone",
            "email",
            "city",
            "state",
            "quantity",
            "preferred_contact_method",
            "message",
            "product_id",
            "campaign_id",
            "source",
            "medium",
            "campaign_name",
            "landing_page",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "consent_given",
            "website",
        )

    def validate_phone(self, value):
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError("Enter a valid mobile number.")
        return value

    def validate_consent_given(self, value):
        if not value:
            raise serializers.ValidationError("Consent is required to submit an enquiry.")
        return value

    def validate_website(self, value):
        if value:
            # Honeypot triggered — treat as a bot submission.
            raise serializers.ValidationError("Invalid submission.")
        return value

    def validate(self, attrs):
        attrs.pop("website", None)
        return attrs


class LeadNoteSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = LeadNote
        fields = ("id", "note", "created_by", "created_at")
        read_only_fields = ("id", "created_by", "created_at")


class LeadStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = LeadStatusHistory
        fields = ("id", "old_status", "new_status", "changed_by", "note", "created_at")


class LeadListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    campaign_name_display = serializers.CharField(
        source="campaign.name", read_only=True, default=None
    )
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=None
    )

    class Meta:
        model = Lead
        fields = (
            "id",
            "lead_number",
            "first_name",
            "last_name",
            "phone",
            "city",
            "product",
            "product_name",
            "source",
            "campaign",
            "campaign_name_display",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_name",
            "is_potential_duplicate",
            "created_at",
        )


class LeadDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    assigned_to_detail = UserSerializer(source="assigned_to", read_only=True)
    status_history = LeadStatusHistorySerializer(many=True, read_only=True)
    notes = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = (
            "id",
            "lead_number",
            "first_name",
            "last_name",
            "phone",
            "email",
            "city",
            "state",
            "quantity",
            "preferred_contact_method",
            "message",
            "product",
            "product_name",
            "campaign",
            "source",
            "medium",
            "campaign_name",
            "landing_page",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_detail",
            "is_potential_duplicate",
            "consent_given",
            "consent_timestamp",
            "status_history",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "lead_number", "created_at", "updated_at")

    def get_notes(self, obj):
        return LeadNoteSerializer(obj.notes.filter(is_deleted=False), many=True).data


class LeadUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = (
            "first_name",
            "last_name",
            "phone",
            "email",
            "city",
            "state",
            "quantity",
            "preferred_contact_method",
            "message",
            "priority",
        )


class LeadAssignSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField()


class LeadStatusUpdateSerializer(serializers.Serializer):
    status = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class LeadNoteCreateSerializer(serializers.Serializer):
    note = serializers.CharField()
