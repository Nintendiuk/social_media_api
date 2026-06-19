from django.urls import reverse
from rest_framework import status


class TestFollowUnfollow:
    def test_follow_user_success(
        self, auth_client, user, other_user
    ):
        url = reverse(
            "user:user-follow",
            kwargs={"pk": other_user.pk},
        )
        res = auth_client.post(url)

        assert res.status_code == status.HTTP_200_OK
        assert user.following.filter(
            pk=other_user.pk
        ).exists()

    def test_follow_already_followed_returns_400(
        self, auth_client, user, other_user
    ):
        user.following.add(other_user)
        res = auth_client.post(
            reverse(
                "user:user-follow",
                kwargs={"pk": other_user.pk},
            )
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_follow_self_returns_400(
        self, auth_client, user
    ):
        res = auth_client.post(
            reverse(
                "user:user-follow",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_follow_nonexistent_user_returns_404(
        self, auth_client
    ):
        res = auth_client.post(
            reverse("user:user-follow", kwargs={"pk": 99999})
        )

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unfollow_user_success(
        self, auth_client, user, other_user
    ):
        user.following.add(other_user)
        res = auth_client.post(
            reverse(
                "user:user-unfollow",
                kwargs={"pk": other_user.pk},
            )
        )

        assert res.status_code == status.HTTP_200_OK
        assert not user.following.filter(
            pk=other_user.pk
        ).exists()

    def test_unfollow_not_followed_returns_400(
        self, auth_client, other_user
    ):
        res = auth_client.post(
            reverse(
                "user:user-unfollow",
                kwargs={"pk": other_user.pk},
            )
        )

        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unfollow_nonexistent_user_returns_404(
        self, auth_client
    ):
        res = auth_client.post(
            reverse(
                "user:user-unfollow",
                kwargs={"pk": 99999},
            )
        )

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_follow(
        self, client, other_user
    ):
        res = client.post(
            reverse(
                "user:user-follow",
                kwargs={"pk": other_user.pk},
            )
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestFollowersList:
    def test_list_followers(
        self, auth_client, user, other_user, third_user
    ):
        other_user.following.add(user)
        third_user.following.add(user)
        res = auth_client.get(
            reverse(
                "user:user-followers",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 2

    def test_list_followers_empty(self, auth_client, user):
        res = auth_client.get(
            reverse(
                "user:user-followers",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_list_followers_nonexistent_user_404(
        self, auth_client
    ):
        res = auth_client.get(
            reverse(
                "user:user-followers",
                kwargs={"pk": 99999},
            )
        )

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_list_followers(
        self, client, user
    ):
        res = client.get(
            reverse(
                "user:user-followers",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED


class TestFollowingList:
    def test_list_following(
        self, auth_client, user, other_user, third_user
    ):
        user.following.add(other_user)
        user.following.add(third_user)
        res = auth_client.get(
            reverse(
                "user:user-following",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 2

    def test_list_following_empty(self, auth_client, user):
        res = auth_client.get(
            reverse(
                "user:user-following",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_200_OK
        assert res.data == []

    def test_list_following_nonexistent_user_404(
        self, auth_client
    ):
        res = auth_client.get(
            reverse(
                "user:user-following",
                kwargs={"pk": 99999},
            )
        )

        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_list_following(
        self, client, user
    ):
        res = client.get(
            reverse(
                "user:user-following",
                kwargs={"pk": user.pk},
            )
        )

        assert res.status_code == status.HTTP_401_UNAUTHORIZED
