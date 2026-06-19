import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from user.models import User
from post.models import Comment, Like, Post


# ── Fixtures ──────────────────────────────────────────────
@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="author@example.com",
        username="author",
        password="StrongPass123!",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@example.com",
        username="otheruser",
        password="StrongPass123!",
    )


@pytest.fixture
def auth_client(client, user):
    res = client.post(
        reverse("user:login"),
        {"email": user.email, "password": "StrongPass123!"},
        format="json",
    )
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {res.data['access']}"
    )
    return client


@pytest.fixture
def post(db, user):
    return Post.objects.create(
        author=user,
        content="A post to engage with #test",
    )


@pytest.fixture
def other_post(db, other_user):
    return Post.objects.create(
        author=other_user,
        content="Another post #python",
    )


@pytest.fixture
def comment(db, user, post):
    return Comment.objects.create(
        author=user,
        post=post,
        content="A test comment",
    )


# ── Likes ─────────────────────────────────────────────────
class TestLikes:
    def test_like_post_success(self, auth_client, user, post):
        url = reverse(
            "post:post-like",
            kwargs={"pk": post.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_200_OK
        assert Like.objects.filter(
            user=user, post=post
        ).exists()

    def test_like_already_liked_returns_400(
        self, auth_client, user, post
    ):
        Like.objects.create(user=user, post=post)
        url = reverse(
            "post:post-like",
            kwargs={"pk": post.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unlike_post_success(
        self, auth_client, user, post
    ):
        Like.objects.create(user=user, post=post)
        url = reverse(
            "post:post-unlike",
            kwargs={"pk": post.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_200_OK
        assert not Like.objects.filter(
            user=user, post=post
        ).exists()

    def test_unlike_not_liked_returns_400(
        self, auth_client, post
    ):
        url = reverse(
            "post:post-unlike",
            kwargs={"pk": post.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_like_nonexistent_post_returns_404(
        self, auth_client
    ):
        url = reverse(
            "post:post-like", kwargs={"pk": 99999}
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unlike_nonexistent_post_returns_404(
        self, auth_client
    ):
        url = reverse(
            "post:post-unlike", kwargs={"pk": 99999}
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_post_detail_includes_like_count(
        self, auth_client, user, post
    ):
        Like.objects.create(user=user, post=post)
        url = reverse(
            "post:post-detail", kwargs={"pk": post.pk}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data["likes_count"] == 1

    def test_unauthenticated_cannot_like(
        self, client, post
    ):
        url = reverse(
            "post:post-like", kwargs={"pk": post.pk}
        )
        res = client.post(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Comments ──────────────────────────────────────────────
class TestComments:
    def test_create_comment_success(
        self, auth_client, user, post
    ):
        url = reverse(
            "post:comment-list-create",
            kwargs={"post_pk": post.pk},
        )
        res = auth_client.post(
            url,
            {"content": "Great post!"},
            format="json",
        )

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["content"] == "Great post!"
        assert (
            res.data["author"]["username"] == user.username
        )

    def test_create_comment_empty_content_fails(
        self, auth_client, post
    ):
        url = reverse(
            "post:comment-list-create",
            kwargs={"post_pk": post.pk},
        )
        res = auth_client.post(
            url, {"content": ""}, format="json"
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_comments_for_post(
        self, auth_client, post, comment
    ):
        url = reverse(
            "post:comment-list-create",
            kwargs={"post_pk": post.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]["content"] == comment.content

    def test_list_comments_on_nonexistent_post_404(
        self, auth_client
    ):
        url = reverse(
            "post:comment-list-create",
            kwargs={"post_pk": 99999},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_update_own_comment(
        self, auth_client, post, comment
    ):
        url = reverse(
            "post:comment-detail",
            kwargs={
                "post_pk": post.pk,
                "pk": comment.pk,
            },
        )
        res = auth_client.patch(
            url,
            {"content": "Updated comment"},
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["content"] == "Updated comment"

    def test_delete_own_comment(
        self, auth_client, post, comment
    ):
        url = reverse(
            "post:comment-detail",
            kwargs={
                "post_pk": post.pk,
                "pk": comment.pk,
            },
        )
        res = auth_client.delete(url)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not Comment.objects.filter(
            pk=comment.pk
        ).exists()

    def test_non_owner_cannot_delete_comment(
        self, auth_client, other_user, post
    ):
        other_comment = Comment.objects.create(
            author=other_user,
            post=post,
            content="Other comment",
        )
        url = reverse(
            "post:comment-detail",
            kwargs={
                "post_pk": post.pk,
                "pk": other_comment.pk,
            },
        )
        res = auth_client.delete(url)

        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_post_detail_includes_comments_count(
        self, auth_client, post, comment
    ):
        url = reverse(
            "post:post-detail", kwargs={"pk": post.pk}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data["comments_count"] == 1

    def test_unauthenticated_cannot_comment(
        self, client, post
    ):
        url = reverse(
            "post:comment-list-create",
            kwargs={"post_pk": post.pk},
        )
        res = client.post(
            url, {"content": "Sneaky!"}, format="json"
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
