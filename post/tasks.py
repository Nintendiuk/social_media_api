from celery import shared_task
from django.utils import timezone

from post.models import Post, ScheduledPost


@shared_task
def publish_scheduled_posts():
    due = ScheduledPost.objects.filter(
        status=ScheduledPost.Status.PENDING,
        scheduled_at__lte=timezone.now(),
    ).select_related("author")

    for sp in due:
        try:
            Post.objects.create(
                author=sp.author,
                content=sp.content,
                media=sp.media or None,
            )
            sp.status = ScheduledPost.Status.PUBLISHED
        except Exception:
            sp.status = ScheduledPost.Status.FAILED
        finally:
            sp.save(update_fields=["status"])
