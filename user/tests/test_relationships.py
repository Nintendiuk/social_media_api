import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from user.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="user@example.com",
        username="mainuser",
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
def third_user(db):
    return User.objects.create_user(
        email="third@example.com",
        username="thirduser",
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


# ── Follow / Unfollow ─────────────────────────────────────
class TestFollowUnfollow:
    def test_follow_user_success(
        self, auth_client, user, other_user
    ):
        url = reverse(
            "user:follow",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_200_OK
        assert user.following.filter(pk=other_user.pk).exists()

    def test_follow_already_followed_returns_400(
        self, auth_client, user, other_user
    ):
        user.following.add(other_user)
        url = reverse(
            "user:follow",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_follow_self_returns_400(self, auth_client, user):
        url = reverse(
            "user:follow",
            kwargs={"pk": user.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_follow_nonexistent_user_returns_404(
        self, auth_client
    ):
        url = reverse("user:follow", kwargs={"pk": 99999})
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unfollow_user_success(
        self, auth_client, user, other_user
    ):
        user.following.add(other_user)
        url = reverse(
            "user:unfollow",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_200_OK
        assert not user.following.filter(
            pk=other_user.pk
        ).exists()

    def test_unfollow_not_followed_returns_400(
        self, auth_client, user, other_user
    ):
        url = reverse(
            "user:unfollow",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unfollow_nonexistent_user_returns_404(
        self, auth_client
    ):
        url = reverse("user:unfollow", kwargs={"pk": 99999})
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_follow(
        self, client, other_user
    ):
        url = reverse(
            "user:follow",
            kwargs={"pk": other_user.pk},
        )
        res = client.post(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Followers list ────────────────────────────────────────
class TestFollowersList:
    def test_list_followers(
        self, auth_client, user, other_user, third_user
    ):
        other_user.following.add(user)
        third_user.following.add(user)

        url = reverse(
            "user:followers",
            kwargs={"pk": user.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 2
        usernames = [u["username"] for u in res.data]
        assert other_user.username in usernames
        assert third_user.username in usernames

    def test_list_followers_empty(
        self, auth_client, user
    ):
        url = reverse(
            "user:followers",
            kwargs={"pk": user.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_list_followers_nonexistent_user_404(
        self, auth_client
    ):
        url = reverse(
            "user:followers", kwargs={"pk": 99999}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_list_followers(
        self, client, user
    ):
        url = reverse(
            "user:followers", kwargs={"pk": user.pk}
        )
        res = client.get(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Following list ────────────────────────────────────────
class TestFollowingList:
    def test_list_following(
        self, auth_client, user, other_user, third_user
    ):
        user.following.add(other_user)
        user.following.add(third_user)

        url = reverse(
            "user:following",
            kwargs={"pk": user.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 2
        usernames = [u["username"] for u in res.data]
        assert other_user.username in usernames
        assert third_user.username in usernames

    def test_list_following_empty(
        self, auth_client, user
    ):
        url = reverse(
            "user:following",
            kwargs={"pk": user.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_list_following_nonexistent_user_404(
        self, auth_client
    ):
        url = reverse(
            "user:following", kwargs={"pk": 99999}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_list_following(
        self, client, user
    ):
        url = reverse(
            "user:following", kwargs={"pk": user.pk}
        )
        res = client.get(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
