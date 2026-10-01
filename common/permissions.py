from rest_framework.permissions import BasePermission

SUPER_ADMIN = "SUPER_ADMIN"
ADMIN = "ADMIN"
SALES_MANAGER = "SALES_MANAGER"
SALES_EXECUTIVE = "SALES_EXECUTIVE"
DOCTOR = "DOCTOR"
PATIENT = "PATIENT"

ADMIN_ROLES = (SUPER_ADMIN, ADMIN)
MANAGER_ROLES = (SUPER_ADMIN, ADMIN, SALES_MANAGER)
CRM_ROLES = (SUPER_ADMIN, ADMIN, SALES_MANAGER, SALES_EXECUTIVE)
CLINICAL_STAFF_ROLES = (SUPER_ADMIN, ADMIN, DOCTOR)


def user_has_role(user, *codes):
    return bool(user and user.is_authenticated and user.has_role(*codes))


class HasAnyRole(BasePermission):
    """Grants access when the user holds at least one of `allowed_roles`."""

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        return user_has_role(request.user, *self.allowed_roles)


class IsSuperAdmin(HasAnyRole):
    allowed_roles = (SUPER_ADMIN,)


class IsAdmin(HasAnyRole):
    """Super Admin or Admin."""

    allowed_roles = ADMIN_ROLES


class IsSalesManagerOrAbove(HasAnyRole):
    allowed_roles = MANAGER_ROLES


class IsCrmUser(HasAnyRole):
    """Anyone working the sales CRM (admins and sales staff) — not doctors or patients."""

    allowed_roles = CRM_ROLES


# Backwards-compatible alias.
IsSalesExecutiveOrAbove = IsCrmUser


class IsClinicalStaff(HasAnyRole):
    allowed_roles = CLINICAL_STAFF_ROLES
