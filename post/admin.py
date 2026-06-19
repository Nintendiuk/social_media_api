from django.contrib import admin
from post.models import (
    Comment,
    Hashtag,
    Like,
    Post,
    ScheduledPost,
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "author__username")


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "created_at")
    search_fields = ("content",)


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = (
        "author",
        "scheduled_at",
        "status",
        "created_at",
    )
    list_filter = ("status",)
