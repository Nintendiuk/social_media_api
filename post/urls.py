from django.urls import path

from post.views import (
    FeedView,
    MyPostsView,
    PostDetailView,
    PostListCreateView,
)

app_name = "post"

urlpatterns = [
    path(
        "",
        PostListCreateView.as_view(),
        name="post-list-create",
    ),
    path(
        "<int:pk>/",
        PostDetailView.as_view(),
        name="post-detail",
    ),
    path(
        "my-posts/",
        MyPostsView.as_view(),
        name="my-posts",
    ),
    path(
        "feed/",
        FeedView.as_view(),
        name="feed",
    ),
]
