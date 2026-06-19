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
        email="docs@example.com",
        username="docsuser",
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


# ── Schema endpoint ───────────────────────────────────────
class TestSchemaEndpoint:
    def test_schema_endpoint_returns_200(self, client):
        url = reverse("schema")
        res = client.get(url)

        assert res.status_code == status.HTTP_200_OK

    def test_schema_is_valid_openapi(self, client):
        url = reverse("schema")
        res = client.get(url)

        assert "openapi" in res.data
        assert "info" in res.data
        assert "paths" in res.data

    def test_schema_has_correct_title(self, client):
        url = reverse("schema")
        res = client.get(url)

        assert res.data["info"]["title"] == "Social Media API"

    def test_schema_has_correct_version(self, client):
        url = reverse("schema")
        res = client.get(url)

        assert res.data["info"]["version"] == "1.0.0"

    def test_schema_includes_jwt_security_scheme(
        self, client
    ):
        url = reverse("schema")
        res = client.get(url)

        components = res.data.get("components", {})
        security_schemes = components.get(
            "securitySchemes", {}
        )
        assert "jwtAuth" in security_schemes

    def test_schema_includes_user_paths(self, client):
        url = reverse("schema")
        res = client.get(url)

        paths = res.data["paths"]
        path_keys = list(paths.keys())
        user_paths = [p for p in path_keys if "/user/" in p]
        assert len(user_paths) > 0

    def test_schema_includes_post_paths(self, client):
        url = reverse("schema")
        res = client.get(url)

        paths = res.data["paths"]
        path_keys = list(paths.keys())
        post_paths = [p for p in path_keys if "/post/" in p]
        assert len(post_paths) > 0

    def test_schema_register_endpoint_documented(
        self, client
    ):
        url = reverse("schema")
        res = client.get(url)

        paths = res.data["paths"]
        register_path = "/api/user/register/"
        assert register_path in paths
        assert "post" in paths[register_path]

    def test_schema_login_endpoint_documented(self, client):
        url = reverse("schema")
        res = client.get(url)

        paths = res.data["paths"]
        login_path = "/api/user/login/"
        assert login_path in paths
        assert "post" in paths[login_path]

    def test_schema_feed_endpoint_documented(self, client):
        url = reverse("schema")
        res = client.get(url)

        paths = res.data["paths"]
        feed_path = "/api/post/feed/"
        assert feed_path in paths
        assert "get" in paths[feed_path]


# ── Swagger UI ────────────────────────────────────────────
class TestSwaggerUI:
    def test_swagger_ui_returns_200(self, client):
        url = reverse("swagger-ui")
        res = client.get(url)

        assert res.status_code == status.HTTP_200_OK

    def test_swagger_ui_returns_html(self, client):
        url = reverse("swagger-ui")
        res = client.get(url)

        assert "text/html" in res["Content-Type"]

    def test_swagger_ui_contains_swagger_ui_bundle(
        self, client
    ):
        url = reverse("swagger-ui")
        res = client.get(url)

        assert b"swagger" in res.content.lower()
