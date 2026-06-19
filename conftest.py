import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from user.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="user@example.com",
        username="testuser",
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
        {
            "email": user.email,
            "password": "StrongPass123!",
        },
        format="json",
    )
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {res.data['access']}"
    )
    return client
