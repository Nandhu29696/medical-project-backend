from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import Role, User, UserRole


class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = "user"
    extra = 0
    fields = ("role", "assigned_by", "assigned_at")
    readonly_fields = ("assigned_by", "assigned_at")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description")
    search_fields = ("code", "name")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "first_name", "last_name", "role_list", "is_active", "is_staff")
    list_filter = ("roles", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name", "phone")
    inlines = [UserRoleInline]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("roles")

    @admin.display(description="Roles")
    def role_list(self, obj):
        return ", ".join(role.code for role in obj.roles.all())
