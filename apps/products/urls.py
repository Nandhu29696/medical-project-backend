from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.products.views import (
    ProductViewSet,
    PublicProductDetailView,
    PublicProductListView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
    path("public/products/", PublicProductListView.as_view(), name="public-product-list"),
    path(
        "public/products/<slug:slug>/",
        PublicProductDetailView.as_view(),
        name="public-product-detail",
    ),
]
