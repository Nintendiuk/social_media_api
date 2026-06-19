from django.contrib import admin

from post.models import Hashtag, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "author__username")


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
