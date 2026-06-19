import pytest
from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from user.models import User
from post.models import Post, ScheduledPost


# ── Fixtures ──────────────────────────────────────────────
@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="scheduler@example.com",
        username="scheduler",
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


@pytest.fixture
def future_time():
    return timezone.now() + timedelta(hours=2)


@pytest.fixture
def scheduled_post(db, user, future_time):
    return ScheduledPost.objects.create(
        author=user,
        content="Scheduled content #celery",
        scheduled_at=future_time,
    )


# ── API: Create scheduled post ────────────────────────────
class TestScheduledPostCreate:
    def test_create_scheduled_post_success(
        self, auth_client, future_time
    ):
        url = reverse("post:scheduled-list-create")
        res = auth_client.post(
            url,
            {
                "content": "Future post #test",
                "scheduled_at": future_time.isoformat(),
            },
            format="json",
        )

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["status"] == "pending"
        assert res.data["content"] == "Future post #test"

    def test_create_scheduled_post_past_time_fails(
        self, auth_client
    ):
        url = reverse("post:scheduled-list-create")
        past = timezone.now() - timedelta(hours=1)
        res = auth_client.post(
            url,
            {
                "content": "Late post",
                "scheduled_at": past.isoformat(),
            },
            format="json",
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_scheduled_post_missing_time_fails(
        self, auth_client
    ):
        url = reverse("post:scheduled-list-create")
        res = auth_client.post(
            url,
            {"content": "No time post"},
            format="json",
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_schedule(self, client):
        url = reverse("post:scheduled-list-create")
        res = client.post(
            url,
            {"content": "Sneaky", "scheduled_at": "2099-01-01"},
            format="json",
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


# ── API: List / detail scheduled posts ───────────────────
class TestScheduledPostList:
    def test_list_own_scheduled_posts(
        self, auth_client, scheduled_post
    ):
        url = reverse("post:scheduled-list-create")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 1
        assert res.data[0]["id"] == scheduled_post.pk

    def test_cannot_see_others_scheduled_posts(
        self, auth_client, db, other_user, future_time
    ):
        ScheduledPost.objects.create(
            author=other_user,
            content="Others secret post",
            scheduled_at=future_time,
        )
        url = reverse("post:scheduled-list-create")
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_delete_own_scheduled_post(
        self, auth_client, scheduled_post
    ):
        url = reverse(
            "post:scheduled-detail",
            kwargs={"pk": scheduled_post.pk},
        )
        res = auth_client.delete(url)

        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not ScheduledPost.objects.filter(
            pk=scheduled_post.pk
        ).exists()

    def test_cannot_delete_others_scheduled_post(
        self, auth_client, db, other_user, future_time
    ):
        other_scheduled = ScheduledPost.objects.create(
            author=other_user,
            content="Others post",
            scheduled_at=future_time,
        )
        url = reverse(
            "post:scheduled-detail",
            kwargs={"pk": other_scheduled.pk},
        )
        res = auth_client.delete(url)

        assert res.status_code == status.HTTP_403_FORBIDDEN


# ── Celery task unit tests ────────────────────────────────
class TestPublishScheduledPostTask:
    def test_task_publishes_pending_post(
        self, db, user, future_time
    ):
        from post.tasks import publish_scheduled_posts

        sp = ScheduledPost.objects.create(
            author=user,
            content="Ready to publish #task",
            scheduled_at=timezone.now() - timedelta(
                seconds=1
            ),
        )

        publish_scheduled_posts()

        sp.refresh_from_db()
        assert sp.status == ScheduledPost.Status.PUBLISHED
        assert Post.objects.filter(
            author=user,
            content=sp.content,
        ).exists()

    def test_task_skips_future_posts(
        self, db, user, future_time
    ):
        from post.tasks import publish_scheduled_posts

        sp = ScheduledPost.objects.create(
            author=user,
            content="Not yet",
            scheduled_at=future_time,
        )

        publish_scheduled_posts()

        sp.refresh_from_db()
        assert sp.status == ScheduledPost.Status.PENDING
        assert not Post.objects.filter(
            author=user, content="Not yet"
        ).exists()

    def test_task_skips_already_published(
        self, db, user
    ):
        from post.tasks import publish_scheduled_posts

        sp = ScheduledPost.objects.create(
            author=user,
            content="Already done",
            scheduled_at=timezone.now() - timedelta(
                seconds=1
            ),
            status=ScheduledPost.Status.PUBLISHED,
        )

        publish_scheduled_posts()

        assert Post.objects.filter(
            author=user, content="Already done"
        ).count() == 0
