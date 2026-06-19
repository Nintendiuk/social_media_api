from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)


class IsAuthorOrReadOnly(BasePermission):
    """
    Write access restricted to the post author.
    Safe methods (GET, HEAD, OPTIONS) are open
    to any authenticated user.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user
