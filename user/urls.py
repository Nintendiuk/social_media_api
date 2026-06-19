from django.urls import path

from django.urls import path

from user.views import (
    FollowersListView,
    FollowingListView,
    FollowView,
    LoginView,
    LogoutView,
    RegisterView,
    UnfollowView,
    UserListView,
    UserProfileDetailView,
    UserProfileMeView,
)

app_name = "user"

urlpatterns = [
    # Auth
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Profiles
    path(
        "profile/me/",
        UserProfileMeView.as_view(),
        name="profile-me",
    ),
    path(
        "profile/<int:pk>/",
        UserProfileDetailView.as_view(),
        name="profile-detail",
    ),
    path(
        "profile/",
        UserListView.as_view(),
        name="profile-list",
    ),
    # Relationships
    path(
        "<int:pk>/follow/",
        FollowView.as_view(),
        name="follow",
    ),
    path(
        "<int:pk>/unfollow/",
        UnfollowView.as_view(),
        name="unfollow",
    ),
    path(
        "<int:pk>/followers/",
        FollowersListView.as_view(),
        name="followers",
    ),
    path(
        "<int:pk>/following/",
        FollowingListView.as_view(),
        name="following",
    ),
]
