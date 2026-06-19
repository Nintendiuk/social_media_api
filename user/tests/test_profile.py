import pytest
from django.urls import reverse
from rest_framework import status


class TestOwnProfile:
    def test_retrieve_own_profile(self, auth_client, user):
        res = auth_client.get(reverse("user:user-me"))

        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == user.email
        assert "password" not in res.data

    def test_update_own_profile(self, auth_client):
        res = auth_client.patch(
            reverse("user:user-me"),
            {"bio": "Hello world!"},
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["bio"] == "Hello world!"

    def test_update_email(self, auth_client):
        res = auth_client.patch(
            reverse("user:user-me"),
            {"email": "new@example.com"},
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == "new@example.com"

    def test_unauthenticated_cannot_access_profile(
        self, client
    ):
        res = client.get(reverse("user:user-me"))

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestOtherProfile:
    def test_retrieve_other_profile_by_id(
        self, auth_client, other_user
    ):
        url = reverse(
            "user:user-detail",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data["username"] == other_user.username

    def test_cannot_update_other_profile(
        self, auth_client, other_user
    ):
        url = reverse(
            "user:user-detail",
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
            "user:user-detail", kwargs={"pk": 99999}
        )
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_404_NOT_FOUND


class TestUserSearch:
    def test_search_by_username(
        self, auth_client, user, other_user
    ):
        res = auth_client.get(
            reverse("user:user-list"),
            {"search": "other"},
        )

        assert res.status_code == status.HTTP_200_OK
        usernames = [
            u["username"] for u in res.data["results"]
        ]
        assert other_user.username in usernames
        assert user.username not in usernames

    def test_search_by_email(
        self, auth_client, other_user
    ):
        res = auth_client.get(
            reverse("user:user-list"),
            {"search": "other@example.com"},
        )

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data["results"]) == 1

    def test_search_no_results(self, auth_client):
        res = auth_client.get(
            reverse("user:user-list"),
            {"search": "zzznomatch"},
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data["results"] == []

    def test_search_unauthenticated_fails(self, client):
        res = client.get(
            reverse("user:user-list"),
            {"search": "test"},
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
