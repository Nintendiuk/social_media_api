from rest_framework.permissions import IsAuthenticated

from post.permissions import IsAuthorOrReadOnly


class AuthorPermissionMixin:
    """
    Shared mixin for all post-app ViewSets.

    Eliminates repeated get_permissions and
    http_method_names across PostViewSet,
    CommentViewSet, and ScheduledPostViewSet.
    """
    http_method_names = [
        "get", "post", "patch", "put",
        "delete", "head", "options",
    ]

    def get_permissions(self):
        if self.action in (
            "partial_update", "update", "destroy"
        ):
            return [
                IsAuthenticated(),
                IsAuthorOrReadOnly(),
            ]
        return [IsAuthenticated()]
