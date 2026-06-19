from django.urls import path, include
from rest_framework.routers import DefaultRouter

from post.views import (
    CommentViewSet,
    PostViewSet,
    ScheduledPostViewSet,
)

app_name = "post"

router = DefaultRouter()
router.register(
    r"scheduled",
    ScheduledPostViewSet,
    basename="scheduled",
)
router.register(r"", PostViewSet, basename="post")

urlpatterns = [
    path(
        "<int:post_pk>/comments/",
        CommentViewSet.as_view(
            {"get": "list", "post": "create"}
        ),
        name="comment-list-create",
    ),
    path(
        "<int:post_pk>/comments/<int:pk>/",
        CommentViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "put": "update",
                "delete": "destroy",
            }
        ),
        name="comment-detail",
    ),
    path("", include(router.urls)),
]
