import pytest
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from post.models import Post, ScheduledPost


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


class TestScheduledPostCreate:
    def test_create_scheduled_post_success(
        self, auth_client, future_time
    ):
        res = auth_client.post(
            reverse("post:scheduled-list"),
            {
                "content": "Future post #test",
                "scheduled_at": future_time.isoformat(),
            },
            format="json",
        )

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["status"] == "pending"

    def test_create_scheduled_post_past_time_fails(
        self, auth_client
    ):
        past = timezone.now() - timedelta(hours=1)
        res = auth_client.post(
            reverse("post:scheduled-list"),
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
        res = auth_client.post(
            reverse("post:scheduled-list"),
            {"content": "No time post"},
            format="json",
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_schedule(self, client):
        res = client.post(
            reverse("post:scheduled-list"),
            {"content": "Sneaky", "scheduled_at": "2099-01-01"},
            format="json",
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestScheduledPostList:
    def test_list_own_scheduled_posts(
        self, auth_client, scheduled_post
    ):
        res = auth_client.get(
            reverse("post:scheduled-list")
        )

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data["results"]) == 1

    def test_cannot_see_others_scheduled_posts(
        self, auth_client, other_user, future_time, db
    ):
        ScheduledPost.objects.create(
            author=other_user,
            content="Others secret post",
            scheduled_at=future_time,
        )
        res = auth_client.get(
            reverse("post:scheduled-list")
        )

        assert res.data["results"] == []

    def test_delete_own_scheduled_post(
        self, auth_client, scheduled_post
    ):
        res = auth_client.delete(
            reverse(
                "post:scheduled-detail",
                kwargs={"pk": scheduled_post.pk},
            )
        )

        assert res.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_delete_others_scheduled_post(
        self, auth_client, other_user, future_time, db
    ):
        other = ScheduledPost.objects.create(
            author=other_user,
            content="Others post",
            scheduled_at=future_time,
        )
        res = auth_client.delete(
            reverse(
                "post:scheduled-detail",
                kwargs={"pk": other.pk},
            )
        )

        assert res.status_code == status.HTTP_403_FORBIDDEN


class TestPublishScheduledPostTask:
    def test_task_publishes_pending_post(self, db, user):
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
            author=user, content=sp.content
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

    def test_task_skips_already_published(self, db, user):
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
