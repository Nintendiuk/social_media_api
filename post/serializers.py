import re
from django.utils import timezone
from rest_framework import serializers

from post.models import Comment, Hashtag, Like, Post, ScheduledPost
from user.serializers import UserProfileSerializer


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ("id", "name")


class CommentSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "author",
            "post",
            "content",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "author",
            "post",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        validated_data["author"] = (
            self.context["request"].user
        )
        validated_data["post"] = (
            self.context["post"]
        )
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "content",
            "media",
            "hashtags",
            "likes_count",
            "comments_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "author",
            "hashtags",
            "likes_count",
            "comments_count",
            "created_at",
            "updated_at",
        )

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def _extract_hashtags(self, content):
        return re.findall(r"#(\w+)", content.lower())

    def _sync_hashtags(self, post, content):
        names = self._extract_hashtags(content)
        tags = []
        for name in names:
            tag, _ = Hashtag.objects.get_or_create(
                name=name
            )
            tags.append(tag)
        post.hashtags.set(tags)

    def create(self, validated_data):
        validated_data["author"] = (
            self.context["request"].user
        )
        post = super().create(validated_data)
        self._sync_hashtags(post, post.content)
        return post

    def update(self, instance, validated_data):
        post = super().update(instance, validated_data)
        self._sync_hashtags(post, post.content)
        return post

class ScheduledPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledPost
        fields = (
            "id",
            "content",
            "media",
            "scheduled_at",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Scheduled time must be in the future."
            )
        return value

    def create(self, validated_data):
        validated_data["author"] = (
            self.context["request"].user
        )
        return super().create(validated_data)
