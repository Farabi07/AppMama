from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """
    Custom permission to allow only Admin users to access certain views.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated and role is 'ADMIN'
        return request.user.is_authenticated and request.user.role == 'admin'


class IsEmployee(BasePermission):
    """
    Custom permission to allow only Employee users to access certain views.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated and role is 'EMPLOYEE'
        return request.user.is_authenticated and request.user.role == 'employee'
