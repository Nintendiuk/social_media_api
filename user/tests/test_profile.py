import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from user.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_payload():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "StrongPass123!",
    }


@pytest.fixture
def other_payload():
    return {
        "email": "other@example.com",
        "username": "otheruser",
        "password": "StrongPass123!",
    }


@pytest.fixture
def user(db, user_payload):
    return User.objects.create_user(**user_payload)


@pytest.fixture
def other_user(db, other_payload):
    return User.objects.create_user(**other_payload)


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


# ── Own profile ───────────────────────────────────────────
class TestOwnProfile:
    def test_retrieve_own_profile(self, auth_client, user):
        url = reverse("user:profile-me")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == user.email
        assert res.data["username"] == user.username
        assert "password" not in res.data

    def test_update_own_profile(self, auth_client, user):
        url = reverse("user:profile-me")
        res = auth_client.patch(
            url, {"bio": "Hello world!"}, format="json"
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["bio"] == "Hello world!"

    def test_update_email(self, auth_client, user):
        url = reverse("user:profile-me")
        res = auth_client.patch(
            url,
            {"email": "new@example.com"},
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == "new@example.com"

    def test_unauthenticated_cannot_access_profile(
        self, client
    ):
        url = reverse("user:profile-me")
        res = client.get(url)

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── Other user profile ────────────────────────────────────
class TestOtherProfile:
    def test_retrieve_other_profile_by_id(
        self, auth_client, other_user
    ):
        url = reverse(
            "user:profile-detail",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data["username"] == other_user.username
        assert "password" not in res.data

    def test_cannot_update_other_profile(
        self, auth_client, other_user
    ):
        url = reverse(
            "user:profile-detail",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.patch(
            url, {"bio": "Hacked!"}, format="json"
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_nonexistent_profile_returns_404(
        self, auth_client
    ):
        url = reverse(
            "user:profile-detail", kwargs={"pk": 99999}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND


# ── Search ────────────────────────────────────────────────
class TestUserSearch:
    def test_search_by_username(
        self, auth_client, user, other_user
    ):
        url = reverse("user:profile-list")
        res = auth_client.get(url, {"search": "other"})

        assert res.status_code == status.HTTP_200_OK
        usernames = [u["username"] for u in res.data]
        assert other_user.username in usernames
        assert user.username not in usernames

    def test_search_by_email(
        self, auth_client, user, other_user
    ):
        url = reverse("user:profile-list")
        res = auth_client.get(
            url, {"search": "other@example.com"}
        )

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]["email"] == other_user.email

    def test_search_no_results(self, auth_client, user):
        url = reverse("user:profile-list")
        res = auth_client.get(
            url, {"search": "zzznomatch"}
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_search_unauthenticated_fails(self, client):
        url = reverse("user:profile-list")
        res = client.get(url, {"search": "test"})

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
