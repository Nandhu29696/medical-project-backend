from django.db import models

from common.models import TimeStampedUUIDModel


class ProductStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ARCHIVED = "ARCHIVED", "Archived"


class Product(TimeStampedUUIDModel):
    """
    Product content fields (composition/benefits/usage/precautions) must only ever
    contain client-approved copy. Do not invent medical claims in code or fixtures.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    composition = models.TextField(blank=True)
    approved_benefits = models.TextField(blank=True)
    approved_usage = models.TextField(blank=True)
    precautions = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    pack_size = models.CharField(max_length=100, blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(
        max_length=16, choices=ProductStatus.choices, default=ProductStatus.DRAFT
    )

    class Meta(TimeStampedUUIDModel.Meta):
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class ProductMediaType(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"
    DOCUMENT = "DOCUMENT", "Document"


class ProductMedia(TimeStampedUUIDModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="products/%Y/%m/")
    media_type = models.CharField(
        max_length=16, choices=ProductMediaType.choices, default=ProductMediaType.IMAGE
    )
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta(TimeStampedUUIDModel.Meta):
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.product.name} media #{self.sort_order}"
