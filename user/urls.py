from django.urls import path

from user.views import (
    LoginView,
    LogoutView,
    RegisterView,
    UserListView,
    UserProfileDetailView,
    UserProfileMeView,
)

app_name = "user"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
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
]
