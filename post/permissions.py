from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)


class IsAuthorOrReadOnly(BasePermission):
    """Write access restricted to the post/comment author."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user
