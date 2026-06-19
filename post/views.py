from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from post.mixins import AuthorPermissionMixin
from post.models import Comment, Like, Post, ScheduledPost
from post.serializers import (
    CommentSerializer,
    PostSerializer,
    ScheduledPostSerializer,
)


# ── Queryset helpers ──────────────────────────────────────

def _post_qs():
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
    return (
        Comment.objects
        .select_related("author")
        .prefetch_related(
            "author__followers",
            "author__following",
        )
    )


# ── Post ViewSet ──────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="List all posts",
        tags=["Posts"],
        parameters=[
            OpenApiParameter(
                name="hashtag",
                description=(
                    "Filter by hashtag (without # symbol)."
                ),
                required=False,
                type=str,
            )
        ],
    ),
    create=extend_schema(
        summary="Create a new post",
        tags=["Posts"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a post",
        tags=["Posts"],
    ),
    partial_update=extend_schema(
        summary="Partially update a post (author only)",
        tags=["Posts"],
    ),
    update=extend_schema(
        summary="Update a post (author only)",
        tags=["Posts"],
    ),
    destroy=extend_schema(
        summary="Delete a post (author only)",
        tags=["Posts"],
    ),
    my_posts=extend_schema(
        summary="List own posts",
        tags=["Posts"],
    ),
    feed=extend_schema(
        summary="Personalised feed",
        tags=["Posts"],
    ),
    like=extend_schema(
        summary="Like a post",
        tags=["Engagement"],
    ),
    unlike=extend_schema(
        summary="Unlike a post",
        tags=["Engagement"],
    ),
)
class PostViewSet(
    AuthorPermissionMixin, viewsets.ModelViewSet
):
    serializer_class = PostSerializer

    def get_queryset(self):
        qs = _post_qs()
        hashtag = self.request.query_params.get("hashtag")
        if hashtag:
            qs = qs.filter(hashtags__name=hashtag.lower())
        return qs

    def _like_response(self, post, action):
        like = Like.objects.filter(
            user=self.request.user, post=post
        ).first()

        if action == "like":
            if like:
                return Response(
                    {"detail": "Already liked this post."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Like.objects.create(
                user=self.request.user, post=post
            )
            return Response(
                {"detail": "Post liked."},
                status=status.HTTP_200_OK,
            )

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

    @action(
        detail=False,
        methods=["get"],
        url_path="my-posts",
    )
    def my_posts(self, request):
        qs = _post_qs().filter(author=request.user)
        return Response(
            self.get_serializer(qs, many=True).data
        )

    @action(detail=False, methods=["get"])
    def feed(self, request):
        ids = list(
            request.user.following.values_list(
                "id", flat=True
            )
        ) + [request.user.id]
        qs = _post_qs().filter(author_id__in=ids)
        return Response(
            self.get_serializer(qs, many=True).data
        )

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        return self._like_response(
            self.get_object(), "like"
        )

    @action(detail=True, methods=["post"])
    def unlike(self, request, pk=None):
        return self._like_response(
            self.get_object(), "unlike"
        )


# ── Comment ViewSet ───────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="List comments on a post",
        tags=["Engagement"],
    ),
    create=extend_schema(
        summary="Add a comment",
        tags=["Engagement"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a comment",
        tags=["Engagement"],
    ),
    partial_update=extend_schema(
        summary="Update a comment (author only)",
        tags=["Engagement"],
    ),
    destroy=extend_schema(
        summary="Delete a comment (author only)",
        tags=["Engagement"],
    ),
)
class CommentViewSet(
    AuthorPermissionMixin, viewsets.ModelViewSet
):
    serializer_class = CommentSerializer

    def _get_post(self):
        return get_object_or_404(
            Post, pk=self.kwargs["post_pk"]
        )

    def get_queryset(self):
        return _comment_qs().filter(post=self._get_post())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["post"] = self._get_post()
        return context


# ── ScheduledPost ViewSet ─────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="List own scheduled posts",
        tags=["Scheduled Posts"],
    ),
    create=extend_schema(
        summary="Schedule a future post",
        tags=["Scheduled Posts"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a scheduled post",
        tags=["Scheduled Posts"],
    ),
    partial_update=extend_schema(
        summary="Update a scheduled post (author only)",
        tags=["Scheduled Posts"],
    ),
    destroy=extend_schema(
        summary="Delete a scheduled post (author only)",
        tags=["Scheduled Posts"],
    ),
)
class ScheduledPostViewSet(
    AuthorPermissionMixin, viewsets.ModelViewSet
):
    serializer_class = ScheduledPostSerializer

    def get_queryset(self):
        return ScheduledPost.objects.filter(
            author=self.request.user
        )

    def get_object(self):
        obj = get_object_or_404(
            ScheduledPost, pk=self.kwargs["pk"]
        )
        self.check_object_permissions(self.request, obj)
        return obj
