import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from user.models import User
from post.models import Hashtag, Post


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
        username="otherauthor",
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
        content="Hello #django world!",
    )


@pytest.fixture
def other_post(db, other_user):
    return Post.objects.create(
        author=other_user,
        content="Other user post #python",
    )


# ── Create post ───────────────────────────────────────────
class TestCreatePost:
    def test_create_post_success(self, auth_client, user):
        url = reverse("post:post-list-create")
        res = auth_client.post(
            url,
            {"content": "My first post #test"},
            format="json",
        )

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["content"] == "My first post #test"
        assert res.data["author"]["username"] == user.username
        assert Post.objects.filter(author=user).exists()

    def test_create_post_extracts_hashtags(
        self, auth_client, user
    ):
        url = reverse("post:post-list-create")
        res = auth_client.post(
            url,
            {"content": "Post with #django and #drf tags"},
            format="json",
        )

        assert res.status_code == status.HTTP_201_CREATED
        hashtags = [h["name"] for h in res.data["hashtags"]]
        assert "django" in hashtags
        assert "drf" in hashtags

    def test_create_post_empty_content_fails(
        self, auth_client
    ):
        url = reverse("post:post-list-create")
        res = auth_client.post(
            url, {"content": ""}, format="json"
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_post_unauthenticated_fails(self, client):
        url = reverse("post:post-list-create")
        res = client.post(
            url, {"content": "Sneaky post"}, format="json"
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Retrieve / own posts ──────────────────────────────────
class TestRetrievePost:
    def test_retrieve_single_post(
        self, auth_client, post
    ):
        url = reverse(
            "post:post-detail",
            kwargs={"pk": post.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == post.pk
        assert "author" in res.data
        assert "hashtags" in res.data

    def test_retrieve_nonexistent_post_returns_404(
        self, auth_client
    ):
        url = reverse(
            "post:post-detail", kwargs={"pk": 99999}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_list_own_posts(
        self, auth_client, user, post, other_post
    ):
        url = reverse("post:my-posts")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert post.pk in ids
        assert other_post.pk not in ids

    def test_unauthenticated_cannot_retrieve_post(
        self, client, post
    ):
        url = reverse(
            "post:post-detail", kwargs={"pk": post.pk}
        )
        res = client.get(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Feed ──────────────────────────────────────────────────
class TestFeed:
    def test_feed_contains_followed_users_posts(
        self, auth_client, user, other_user, other_post
    ):
        user.following.add(other_user)

        url = reverse("post:feed")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert other_post.pk in ids

    def test_feed_excludes_unfollowed_users_posts(
        self, auth_client, user, other_post
    ):
        # user does NOT follow other_user
        url = reverse("post:feed")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert other_post.pk not in ids

    def test_feed_includes_own_posts(
        self, auth_client, user, post
    ):
        url = reverse("post:feed")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert post.pk in ids

    def test_feed_ordered_newest_first(
        self, auth_client, user, other_user
    ):
        user.following.add(other_user)
        p1 = Post.objects.create(
            author=other_user, content="Older post"
        )
        p2 = Post.objects.create(
            author=other_user, content="Newer post"
        )

        url = reverse("post:feed")
        res = auth_client.get(url)

        ids = [p["id"] for p in res.data]
        assert ids.index(p2.pk) < ids.index(p1.pk)

    def test_feed_unauthenticated_fails(self, client):
        url = reverse("post:feed")
        res = client.get(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Hashtag filter ────────────────────────────────────────
class TestHashtagFilter:
    def test_filter_posts_by_hashtag(
        self, auth_client, user, db
    ):
        p1 = Post.objects.create(
            author=user, content="Post about #django"
        )
        p2 = Post.objects.create(
            author=user, content="Post about #python"
        )
        tag = Hashtag.objects.create(name="django")
        tag.posts.add(p1)

        url = reverse("post:post-list-create")
        res = auth_client.get(url, {"hashtag": "django"})

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert p1.pk in ids
        assert p2.pk not in ids

    def test_filter_nonexistent_hashtag_returns_empty(
        self, auth_client, post
    ):
        url = reverse("post:post-list-create")
        res = auth_client.get(
            url, {"hashtag": "zzznomatch"}
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_list_all_posts_without_filter(
        self, auth_client, post, other_post
    ):
        url = reverse("post:post-list-create")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert post.pk in ids
        assert other_post.pk in ids


# ── Permissions ───────────────────────────────────────────
class TestPostPermissions:
    def test_owner_can_delete_own_post(
        self, auth_client, post
    ):
        url = reverse(
            "post:post-detail", kwargs={"pk": post.pk}
        )
        res = auth_client.delete(url)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not Post.objects.filter(pk=post.pk).exists()

    def test_non_owner_cannot_delete_post(
        self, auth_client, other_post
    ):
        url = reverse(
            "post:post-detail",
            kwargs={"pk": other_post.pk},
        )
        res = auth_client.delete(url)

        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_owner_can_update_own_post(
        self, auth_client, post
    ):
        url = reverse(
            "post:post-detail", kwargs={"pk": post.pk}
        )
        res = auth_client.patch(
            url,
            {"content": "Updated content #new"},
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["content"] == "Updated content #new"

    def test_non_owner_cannot_update_post(
        self, auth_client, other_post
    ):
        url = reverse(
            "post:post-detail",
            kwargs={"pk": other_post.pk},
        )
        res = auth_client.patch(
            url,
            {"content": "Hacked!"},
            format="json",
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN
