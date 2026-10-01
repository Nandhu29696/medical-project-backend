from rest_framework import generics, permissions, viewsets

from apps.audit.services import log_action
from apps.products.models import Product, ProductStatus
from apps.products.serializers import ProductPublicSerializer, ProductSerializer
from common.mixins import EnvelopeMixin
from common.permissions import IsAdmin


class ProductViewSet(EnvelopeMixin, viewsets.ModelViewSet):
    """Admin/CRM product management. Only Super Admin / Admin can write; all roles can read."""

    queryset = Product.objects.all().prefetch_related("media")
    serializer_class = ProductSerializer
    filterset_fields = ["status"]
    search_fields = ["name", "slug"]
    ordering_fields = ["created_at", "name", "selling_price"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="PRODUCT_CREATED",
            entity_type="Product",
            entity_id=instance.id,
            new_values=serializer.data,
            request=self.request,
        )

    def perform_update(self, serializer):
        old_values = ProductSerializer(self.get_object()).data
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action="PRODUCT_UPDATED",
            entity_type="Product",
            entity_id=instance.id,
            old_values=old_values,
            new_values=serializer.data,
            request=self.request,
        )


class PublicProductListView(generics.ListAPIView):
    """Public website product catalog — only active products, no internal fields."""

    queryset = Product.objects.filter(status=ProductStatus.ACTIVE).prefetch_related("media")
    serializer_class = ProductPublicSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class PublicProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(status=ProductStatus.ACTIVE).prefetch_related("media")
    serializer_class = ProductPublicSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    lookup_field = "slug"
