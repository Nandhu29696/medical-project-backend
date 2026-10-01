from rest_framework import serializers

from apps.products.models import Product, ProductMedia


class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ("id", "file", "media_type", "alt_text", "sort_order", "is_primary")


class ProductSerializer(serializers.ModelSerializer):
    """Full product representation for authenticated CRM/admin users."""

    media = ProductMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "composition",
            "approved_benefits",
            "approved_usage",
            "precautions",
            "manufacturer",
            "pack_size",
            "mrp",
            "selling_price",
            "gst_percentage",
            "status",
            "media",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProductPublicSerializer(serializers.ModelSerializer):
    """Reduced product representation safe to expose on the public website."""

    media = ProductMediaSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "approved_benefits",
            "approved_usage",
            "precautions",
            "pack_size",
            "mrp",
            "selling_price",
            "media",
        )
