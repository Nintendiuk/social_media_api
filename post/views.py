from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from post.models import Hashtag, Post
from post.permissions import IsAuthorOrReadOnly
from post.serializers import PostSerializer


def _post_queryset_optimised():
    """
    Central helper that returns a fully optimised
    Post queryset.

    N+1 prevention:
    - select_related("author"): one JOIN for the author
      row instead of one query per post.
    - prefetch_related("author__followers",
                       "author__following"):
      batch-loads follower counts used by the nested
      UserProfileSerializer.
    - prefetch_related("hashtags"): batch-loads all
      hashtag rows in a single IN query instead of
      one query per post.
    """
    return (
        Post.objects.select_related("author")
        .prefetch_related(
            "author__followers",
            "author__following",
            "hashtags",
        )
    )


class PostListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/post/          → list all posts
                               (filter: ?hashtag=<name>)
    POST /api/post/          → create a new post
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        qs = _post_queryset_optimised()
        hashtag = self.request.query_params.get("hashtag")
        if hashtag:
            qs = qs.filter(
                hashtags__name=hashtag.lower()
            )
        return qs


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/post/<pk>/  → retrieve post
    PATCH  /api/post/<pk>/  → update (author only)
    DELETE /api/post/<pk>/  → delete (author only)
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        return _post_queryset_optimised()


class MyPostsView(generics.ListAPIView):
    """
    GET /api/post/my-posts/
    Returns only the authenticated user's own posts.
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return _post_queryset_optimised().filter(
            author=self.request.user
        )


class FeedView(generics.ListAPIView):
    """
    GET /api/post/feed/
    Returns posts from the authenticated user and
    everyone they follow, ordered newest first.

    N+1 prevention: same optimised queryset helper;
    the following filter is a single IN subquery
    against the M2M join table.
    """
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        following_ids = user.following.values_list(
            "id", flat=True
        )
        return _post_queryset_optimised().filter(
            author_id__in=list(following_ids) + [user.id]
        )
