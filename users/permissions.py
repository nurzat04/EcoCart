# users/permissions.py
from rest_framework.permissions import BasePermission

class IsVendorOrAdmin(BasePermission):
    """
    只有供应商 (vendor) 或管理员 (admin) 才有权限进行某些操作。
    """
    def has_permission(self, request, view):
        user = request.user
        return user.is_vendor or user.is_admin

class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'is_vendor', False)