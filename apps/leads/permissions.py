from rest_framework.permissions import BasePermission

from common.permissions import CRM_ROLES, MANAGER_ROLES, user_has_role


class LeadObjectPermission(BasePermission):
    """
    SUPER_ADMIN / ADMIN / SALES_MANAGER: full access to all leads.
    SALES_EXECUTIVE: read/write only leads assigned to them.
    DOCTOR / PATIENT: no access to the sales CRM.
    """

    def has_permission(self, request, view):
        return user_has_role(request.user, *CRM_ROLES)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.has_role(*MANAGER_ROLES):
            return True
        return obj.assigned_to_id == user.id
