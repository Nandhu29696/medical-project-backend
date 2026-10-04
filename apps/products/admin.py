from django.contrib import admin

from apps.products.models import Product, ProductMedia


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "selling_price", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductMediaInline]
