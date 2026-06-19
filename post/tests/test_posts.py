import pytest
from django.urls import reverse
from rest_framework import status

from post.models import Hashtag, Post


@pytest.fixture
def post(db, user):
    return Post.objects.create(
        author=user, content="Hello #django world!"
    )


@pytest.fixture
def other_post(db, other_user):
    return Post.objects.create(
        author=other_user, content="Other post #python"
    )


class TestCreatePost:
    def test_create_post_success(self, auth_client, user):
        res = auth_client.post(
            reverse("post:post-list"),
            {"content": "My first post #test"},
            format="json",
        )

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["content"] == "My first post #test"
        assert (
            res.data["author"]["username"] == user.username
        )

    def test_create_post_extracts_hashtags(
        self, auth_client
    ):
        res = auth_client.post(
            reverse("post:post-list"),
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
        res = auth_client.post(
            reverse("post:post-list"),
            {"content": ""},
            format="json",
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_post_unauthenticated_fails(self, client):
        res = client.post(
            reverse("post:post-list"),
            {"content": "Sneaky"},
            format="json",
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestRetrievePost:
    def test_retrieve_single_post(self, auth_client, post):
        res = auth_client.get(
            reverse("post:post-detail", kwargs={"pk": post.pk})
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["id"] == post.pk

    def test_retrieve_nonexistent_post_returns_404(
        self, auth_client
    ):
        res = auth_client.get(
            reverse("post:post-detail", kwargs={"pk": 99999})
        )

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_list_own_posts(
        self, auth_client, post, other_post
    ):
        res = auth_client.get(reverse("post:post-my-posts"))

        assert res.status_code == status.HTTP_200_OK
        ids = [p["id"] for p in res.data]
        assert post.pk in ids
        assert other_post.pk not in ids

    def test_unauthenticated_cannot_retrieve_post(
        self, client, post
    ):
        res = client.get(
            reverse("post:post-detail", kwargs={"pk": post.pk})
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestFeed:
    def test_feed_contains_followed_users_posts(
        self, auth_client, user, other_user, other_post
    ):
        user.following.add(other_user)
        res = auth_client.get(reverse("post:post-feed"))

        assert res.status_code == status.HTTP_200_OK
        assert other_post.pk in [
            p["id"] for p in res.data
        ]

    def test_feed_excludes_unfollowed_users_posts(
        self, auth_client, other_post
    ):
        res = auth_client.get(reverse("post:post-feed"))

        assert other_post.pk not in [
            p["id"] for p in res.data
        ]

    def test_feed_includes_own_posts(
        self, auth_client, post
    ):
        res = auth_client.get(reverse("post:post-feed"))

        assert post.pk in [p["id"] for p in res.data]

    def test_feed_ordered_newest_first(
        self, auth_client, user, other_user
    ):
        user.following.add(other_user)
        p1 = Post.objects.create(
            author=other_user, content="Older"
        )
        p2 = Post.objects.create(
            author=other_user, content="Newer"
        )
        res = auth_client.get(reverse("post:post-feed"))

        ids = [p["id"] for p in res.data]
        assert ids.index(p2.pk) < ids.index(p1.pk)

    def test_feed_unauthenticated_fails(self, client):
        res = client.get(reverse("post:post-feed"))

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


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

        res = auth_client.get(
            reverse("post:post-list"),
            {"hashtag": "django"},
        )

        ids = [p["id"] for p in res.data["results"]]
        assert p1.pk in ids
        assert p2.pk not in ids

    def test_filter_nonexistent_hashtag_returns_empty(
        self, auth_client
    ):
        res = auth_client.get(
            reverse("post:post-list"),
            {"hashtag": "zzznomatch"},
        )

        assert res.data["results"] == []

    def test_list_all_posts_without_filter(
        self, auth_client, post, other_post
    ):
        res = auth_client.get(reverse("post:post-list"))

        ids = [p["id"] for p in res.data["results"]]
        assert post.pk in ids
        assert other_post.pk in ids


class TestPostPermissions:
    def test_owner_can_delete_own_post(
        self, auth_client, post
    ):
        res = auth_client.delete(
            reverse("post:post-detail", kwargs={"pk": post.pk})
        )

        assert res.status_code == status.HTTP_204_NO_CONTENT

    def test_non_owner_cannot_delete_post(
        self, auth_client, other_post
    ):
        res = auth_client.delete(
            reverse(
                "post:post-detail",
                kwargs={"pk": other_post.pk},
            )
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_owner_can_update_own_post(
        self, auth_client, post
    ):
        res = auth_client.patch(
            reverse("post:post-detail", kwargs={"pk": post.pk}),
            {"content": "Updated #new"},
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["content"] == "Updated #new"

    def test_non_owner_cannot_update_post(
        self, auth_client, other_post
    ):
        res = auth_client.patch(
            reverse(
                "post:post-detail",
                kwargs={"pk": other_post.pk},
            ),
            {"content": "Hacked!"},
            format="json",
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN
