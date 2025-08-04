# api, permissions.py:
from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class FullDjangoModelPermission(permissions.DjangoModelPermissions):  # overriding DjangoModelPermissions
    def __init__(self):
        self.perms_map['GET'] = ['%(app_label)s.view_%(model_name)s']
        
"""
^
By default, GET requests (e.g., listing or retrieving resources) don't require any model permissions when using DjangoModelPermissions.
But with this override, users must explicitly have the view_<model> permission to access views with GET.
--
see rbac, now user has be in a group which gives him view permission.
--
In Django, permissions can be assigned to 1. Users directly, or 2. Groups, and then users can be added to those groups.
"""