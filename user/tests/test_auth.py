import pytest
from django.urls import reverse
from rest_framework import status

from user.models import User


@pytest.fixture
def user_payload():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "StrongPass123!",
    }


@pytest.fixture
def registered_user(db, user_payload):
    return User.objects.create_user(**user_payload)


class TestRegistration:
    def test_register_success(
        self, client, db, user_payload
    ):
        url = reverse("user:register")
        res = client.post(
            url, user_payload, format="json"
        )

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["email"] == user_payload["email"]
        assert "password" not in res.data

    def test_register_duplicate_email_fails(
        self, client, db, user_payload, registered_user
    ):
        url = reverse("user:register")
        res = client.post(
            url, user_payload, format="json"
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password_fails(
        self, client, db, user_payload
    ):
        user_payload["password"] = "123"
        url = reverse("user:register")
        res = client.post(
            url, user_payload, format="json"
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_email_fails(self, client, db):
        url = reverse("user:register")
        res = client.post(
            url,
            {"username": "u", "password": "StrongPass123!"},
            format="json",
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST


class TestLogin:
    def test_login_success_returns_tokens(
        self, client, db, registered_user, user_payload
    ):
        url = reverse("user:login")
        res = client.post(
            url,
            {
                "email": user_payload["email"],
                "password": user_payload["password"],
            },
            format="json",
        )

        assert res.status_code == status.HTTP_200_OK
        assert "access" in res.data
        assert "refresh" in res.data

    def test_login_wrong_password_fails(
        self, client, db, registered_user, user_payload
    ):
        url = reverse("user:login")
        res = client.post(
            url,
            {
                "email": user_payload["email"],
                "password": "wrongpass",
            },
            format="json",
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user_fails(self, client, db):
        url = reverse("user:login")
        res = client.post(
            url,
            {"email": "no@one.com", "password": "pass"},
            format="json",
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    def test_logout_success(
        self, client, db, registered_user, user_payload
    ):
        login_res = client.post(
            reverse("user:login"),
            {
                "email": user_payload["email"],
                "password": user_payload["password"],
            },
            format="json",
        )
        client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {login_res.data['access']}"
            )
        )
        res = client.post(
            reverse("user:logout"),
            {"refresh": login_res.data["refresh"]},
            format="json",
        )

        assert res.status_code == status.HTTP_205_RESET_CONTENT

    def test_logout_unauthenticated_fails(self, client, db):
        res = client.post(
            reverse("user:logout"),
            {"refresh": "faketoken"},
            format="json",
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
