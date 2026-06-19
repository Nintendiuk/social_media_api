from django.shortcuts import get_object_or_404
from rest_framework import generics, filters, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import User
from user.permissions import IsOwnerOrReadOnly
from user.serializers import (
    FollowSerializer,
    LoginSerializer,
    LogoutSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = UserRegistrationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)

class UserProfileMeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/user/profile/me/  → own profile
    PATCH/PUT                   → update own profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/user/profile/<pk>/  → any user profile
    PATCH /api/user/profile/<pk>/  → owner only
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)

    def get_queryset(self):
        # N+1 prevention: prefetch follower counts in one query
        return User.objects.prefetch_related(
            "followers", "following"
        )


class UserListView(generics.ListAPIView):
    """
    GET /api/user/profile/?search=<term>
    Searches username and email fields.
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ("username", "email")

    def get_queryset(self):
        # N+1 prevention: prefetch follower counts in one query
        return User.objects.prefetch_related(
            "followers", "following"
        )

class FollowView(APIView):
    """
    POST /api/user/<pk>/follow/
    Authenticated user follows target user.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        if target == request.user:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.following.filter(pk=target.pk).exists():
            return Response(
                {"detail": "Already following this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.following.add(target)
        return Response(
            {"detail": f"Now following {target.username}."},
            status=status.HTTP_200_OK,
        )


class UnfollowView(APIView):
    """
    POST /api/user/<pk>/unfollow/
    Authenticated user unfollows target user.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        if not request.user.following.filter(
            pk=target.pk
        ).exists():
            return Response(
                {"detail": "You are not following this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.following.remove(target)
        return Response(
            {
                "detail": (
                    f"Unfollowed {target.username}."
                )
            },
            status=status.HTTP_200_OK,
        )


class FollowersListView(generics.ListAPIView):
    """
    GET /api/user/<pk>/followers/
    Returns all users who follow the target user.
    N+1 fix: prefetch_related on followers/following
    for count fields rendered by FollowSerializer.
    """
    serializer_class = FollowSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        target = get_object_or_404(User, pk=self.kwargs["pk"])
        return target.followers.prefetch_related(
            "followers", "following"
        )


class FollowingListView(generics.ListAPIView):
    """
    GET /api/user/<pk>/following/
    Returns all users the target user follows.
    N+1 fix: prefetch_related on followers/following
    for count fields rendered by FollowSerializer.
    """
    serializer_class = FollowSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        target = get_object_or_404(User, pk=self.kwargs["pk"])
        return target.following.prefetch_related(
            "followers", "following"
        )
