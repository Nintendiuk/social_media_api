from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from post.models import (
    Comment,
    Hashtag,
    Like,
    Post,
    ScheduledPost,
)
from post.permissions import IsAuthorOrReadOnly
from post.serializers import (
    CommentSerializer,
    PostSerializer,
    ScheduledPostSerializer,
)


def _post_qs():
    """
    Fully optimised Post queryset.

    N+1 prevention:
    - select_related("author"): one JOIN for author row.
    - prefetch_related("author__followers",
                       "author__following"): batch-load
      follower counts used by UserProfileSerializer.
    - prefetch_related("hashtags"): single IN query.
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
@extend_schema_view(
    get=extend_schema(
        summary="List all posts",
        description=(
            "Returns all posts ordered by newest first. "
            "Optionally filter by hashtag using "
            "`?hashtag=<name>`."
        ),
        tags=["Posts"],
        parameters=[
            OpenApiParameter(
                name="hashtag",
                description=(
                    "Filter posts by hashtag name "
                    "(without the # symbol)."
                ),
                required=False,
                type=str,
            )
        ],
    ),
    post=extend_schema(
        summary="Create a new post",
        description=(
            "Creates a post for the authenticated user. "
            "Hashtags are extracted automatically from "
            "content using #word syntax."
        ),
        tags=["Posts"],
    ),
)
class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = _post_qs()
        hashtag = self.request.query_params.get("hashtag")
        if hashtag:
            qs = qs.filter(
                hashtags__name=hashtag.lower()
            )
        return qs


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve a post",
        tags=["Posts"],
    ),
    patch=extend_schema(
        summary="Partially update a post (author only)",
        tags=["Posts"],
    ),
    put=extend_schema(
        summary="Update a post (author only)",
        tags=["Posts"],
    ),
    delete=extend_schema(
        summary="Delete a post (author only)",
        tags=["Posts"],
    ),
)
class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        return _post_qs()


@extend_schema_view(
    get=extend_schema(
        summary="List authenticated user's own posts",
        tags=["Posts"],
    )
)
class MyPostsView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return _post_qs().filter(author=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve personalised post feed",
        description=(
            "Returns posts from the authenticated user "
            "and everyone they follow, "
            "ordered newest first."
        ),
        tags=["Posts"],
    )
)
class FeedView(generics.ListAPIView):
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
@extend_schema(tags=["Engagement"])
class PostLikeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Like a post",
        description=(
            "Authenticated user likes the target post. "
            "Returns 400 if already liked."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                },
            }
        },
    )
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


@extend_schema(tags=["Engagement"])
class PostUnlikeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Unlike a post",
        description=(
            "Authenticated user removes their like "
            "from the target post. "
            "Returns 400 if not yet liked."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                },
            }
        },
    )
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        like = Like.objects.filter(
            user=request.user, post=post
        ).first()

        if not like:
            return Response(
                {
                    "detail": (
                        "You have not liked this post."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        like.delete()
        return Response(
            {"detail": "Post unliked."},
            status=status.HTTP_200_OK,
        )


# ── Comment views ─────────────────────────────────────────
@extend_schema_view(
    get=extend_schema(
        summary="List comments on a post",
        tags=["Engagement"],
    ),
    post=extend_schema(
        summary="Add a comment to a post",
        tags=["Engagement"],
    ),
)
class CommentListCreateView(generics.ListCreateAPIView):
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


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve a comment",
        tags=["Engagement"],
    ),
    patch=extend_schema(
        summary="Update a comment (author only)",
        tags=["Engagement"],
    ),
    delete=extend_schema(
        summary="Delete a comment (author only)",
        tags=["Engagement"],
    ),
)
class CommentDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        get_object_or_404(Post, pk=self.kwargs["post_pk"])
        return _comment_qs()


# ── Scheduled post views ──────────────────────────────────
@extend_schema_view(
    get=extend_schema(
        summary="List own scheduled posts",
        description=(
            "Returns only the authenticated user's "
            "own scheduled posts."
        ),
        tags=["Scheduled Posts"],
    ),
    post=extend_schema(
        summary="Schedule a post for future publishing",
        description=(
            "Creates a scheduled post that Celery will "
            "publish automatically at `scheduled_at`. "
            "Time must be in the future."
        ),
        tags=["Scheduled Posts"],
    ),
)
class ScheduledPostListCreateView(
    generics.ListCreateAPIView
):
    serializer_class = ScheduledPostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ScheduledPost.objects.filter(
            author=self.request.user
        )


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve a scheduled post",
        tags=["Scheduled Posts"],
    ),
    patch=extend_schema(
        summary="Update a scheduled post (author only)",
        tags=["Scheduled Posts"],
    ),
    delete=extend_schema(
        summary="Delete a scheduled post (author only)",
        tags=["Scheduled Posts"],
    ),
)
class ScheduledPostDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
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
