from django.urls import path, include
from rest_framework.routers import DefaultRouter

from user.views import (
    LoginView,
    LogoutView,
    RegisterView,
    UserViewSet,
)

app_name = "user"

router = DefaultRouter()
router.register(r"", UserViewSet, basename="user")

urlpatterns = [
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path("", include(router.urls)),
]
