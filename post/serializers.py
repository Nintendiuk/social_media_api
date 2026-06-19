import re
from rest_framework import serializers

from post.models import Hashtag, Post
from user.serializers import UserProfileSerializer


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ("id", "name")


class PostSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "content",
            "media",
            "hashtags",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "author",
            "hashtags",
            "created_at",
            "updated_at",
        )

    def _extract_hashtags(self, content):
        """Parse #word tokens from post content."""
        return re.findall(r"#(\w+)", content.lower())

    def _sync_hashtags(self, post, content):
        """
        Create-or-get each hashtag and attach to post.
        Clears stale tags on update so the set stays
        in sync with current content.
        """
        names = self._extract_hashtags(content)
        tags = []
        for name in names:
            tag, _ = Hashtag.objects.get_or_create(name=name)
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
