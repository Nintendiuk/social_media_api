from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from post.models import Comment, Hashtag, Like, Post, ScheduledPost
from post.serializers import (
    CommentSerializer,
    PostSerializer,
    ScheduledPostSerializer,
)

from post.models import Comment, Hashtag, Like, Post
from post.permissions import IsAuthorOrReadOnly
from post.serializers import CommentSerializer, PostSerializer


def _post_qs():
    """
    Fully optimised Post queryset.

    N+1 prevention:
    - select_related("author"): one JOIN for author row.
    - prefetch_related("author__followers",
                       "author__following"): batch-load
      follower counts used by UserProfileSerializer.
    - prefetch_related("hashtags"): single IN query for
      all hashtag rows.
    - prefetch_related("likes", "comments"): single IN
      query each for like/comment counts.
    """
    return (
        Post.objects
        .select_related("author")
        .prefetch_related(
            "author__followers",
            "author__following",
            "hashtags",
            "likes",
            "comments",
        )
    )


def _comment_qs():
    """
    Optimised Comment queryset.

    N+1 prevention:
    - select_related("author"): one JOIN for author row.
    - prefetch_related("author__followers",
                       "author__following"): batch-load
      counts for nested UserProfileSerializer.
    """
    return (
        Comment.objects
        .select_related("author")
        .prefetch_related(
            "author__followers",
            "author__following",
        )
    )


# ── Post views ────────────────────────────────────────────
class PostListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/post/        → list all posts
                             (filter: ?hashtag=<name>)
    POST /api/post/        → create a new post
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = _post_qs()
        hashtag = self.request.query_params.get("hashtag")
        if hashtag:
            qs = qs.filter(hashtags__name=hashtag.lower())
        return qs


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/post/<pk>/  → retrieve post
    PATCH  /api/post/<pk>/  → update  (author only)
    DELETE /api/post/<pk>/  → delete  (author only)
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        return _post_qs()


class MyPostsView(generics.ListAPIView):
    """GET /api/post/my-posts/  → own posts only"""
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return _post_qs().filter(author=self.request.user)


class FeedView(generics.ListAPIView):
    """
    GET /api/post/feed/
    Posts from the authenticated user + everyone they follow,
    newest first.
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        following_ids = user.following.values_list(
            "id", flat=True
        )
        return _post_qs().filter(
            author_id__in=list(following_ids) + [user.id]
        )


# ── Like views ────────────────────────────────────────────
class PostLikeView(APIView):
    """POST /api/post/<pk>/like/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)

        if Like.objects.filter(
            user=request.user, post=post
        ).exists():
            return Response(
                {"detail": "Already liked this post."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Like.objects.create(user=request.user, post=post)
        return Response(
            {"detail": "Post liked."},
            status=status.HTTP_200_OK,
        )


class PostUnlikeView(APIView):
    """POST /api/post/<pk>/unlike/"""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        like = Like.objects.filter(
            user=request.user, post=post
        ).first()

        if not like:
            return Response(
                {"detail": "You have not liked this post."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        like.delete()
        return Response(
            {"detail": "Post unliked."},
            status=status.HTTP_200_OK,
        )


# ── Comment views ─────────────────────────────────────────
class CommentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/post/<post_pk>/comments/  → list comments
    POST /api/post/<post_pk>/comments/  → add comment
    """
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated,)

    def _get_post(self):
        return get_object_or_404(
            Post, pk=self.kwargs["post_pk"]
        )

    def get_queryset(self):
        post = self._get_post()
        return _comment_qs().filter(post=post)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["post"] = self._get_post()
        return context


class CommentDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    GET    /api/post/<post_pk>/comments/<pk>/
    PATCH  /api/post/<post_pk>/comments/<pk>/
    DELETE /api/post/<post_pk>/comments/<pk>/
    """
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        get_object_or_404(Post, pk=self.kwargs["post_pk"])
        return _comment_qs()

class ScheduledPostListCreateView(
    generics.ListCreateAPIView
):
    """
    GET  /api/post/scheduled/  → own scheduled posts
    POST /api/post/scheduled/  → create scheduled post
    """
    serializer_class = ScheduledPostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ScheduledPost.objects.filter(
            author=self.request.user
        )


class ScheduledPostDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    GET    /api/post/scheduled/<pk>/
    PATCH  /api/post/scheduled/<pk>/
    DELETE /api/post/scheduled/<pk>/
    """
    serializer_class = ScheduledPostSerializer
    permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        return ScheduledPost.objects.filter(
            author=self.request.user
        )

    def get_object(self):
        obj = get_object_or_404(
            ScheduledPost,
            pk=self.kwargs["pk"],
        )
        self.check_object_permissions(self.request, obj)
        return obj
