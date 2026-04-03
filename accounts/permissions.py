from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    """Only users with the 'admin' role (or Django superuser) may proceed."""

    message = 'Admin role required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role == 'admin' or request.user.is_superuser)
        )


class IsAnalystOrAdmin(BasePermission):
    """Users with 'analyst' or 'admin' roles (or Django superuser) may proceed."""

    message = 'Analyst or Admin role required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role in ('analyst', 'admin') or request.user.is_superuser)
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level permission: the requesting user must own the object, or be an admin."""

    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        return getattr(obj, 'user', None) == request.user
