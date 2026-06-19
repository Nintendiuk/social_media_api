from django.urls import path

from post.views import (
    CommentDetailView,
    CommentListCreateView,
    FeedView,
    MyPostsView,
    PostDetailView,
    PostLikeView,
    PostListCreateView,
    PostUnlikeView,
    ScheduledPostDetailView,
    ScheduledPostListCreateView,
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
    path(
        "<int:pk>/like/",
        PostLikeView.as_view(),
        name="post-like",
    ),
    path(
        "<int:pk>/unlike/",
        PostUnlikeView.as_view(),
        name="post-unlike",
    ),
    path(
        "<int:post_pk>/comments/",
        CommentListCreateView.as_view(),
        name="comment-list-create",
    ),
    path(
        "<int:post_pk>/comments/<int:pk>/",
        CommentDetailView.as_view(),
        name="comment-detail",
    ),
path(
        "scheduled/",
        ScheduledPostListCreateView.as_view(),
        name="scheduled-list-create",
    ),
    path(
        "scheduled/<int:pk>/",
        ScheduledPostDetailView.as_view(),
        name="scheduled-detail",
    ),
]
