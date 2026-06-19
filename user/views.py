from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)
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


@extend_schema(tags=["Auth"])
class RegisterView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Register a new user",
        description=(
            "Creates a new user account. "
            "Returns the created user (no password). "
            "No authentication required."
        ),
        request=UserRegistrationSerializer,
        responses={201: UserRegistrationSerializer},
        examples=[
            OpenApiExample(
                "Registration example",
                value={
                    "email": "user@example.com",
                    "username": "myusername",
                    "password": "StrongPass123!",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Auth"])
class LoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Obtain JWT token pair",
        description=(
            "Authenticates with email and password. "
            "Returns access and refresh JWT tokens."
        ),
        request=LoginSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string"},
                    "refresh": {"type": "string"},
                },
            }
        },
        examples=[
            OpenApiExample(
                "Login example",
                value={
                    "email": "user@example.com",
                    "password": "StrongPass123!",
                },
                request_only=True,
            )
        ],
    )
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


@extend_schema(tags=["Auth"])
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Blacklist refresh token (logout)",
        description=(
            "Invalidates the provided refresh token. "
            "The access token expires naturally."
        ),
        request=LogoutSerializer,
        responses={205: None},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(tags=["Profiles"])
class UserProfileMeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/user/profile/me/  → own profile
    PATCH/PUT                   → update own profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Retrieve own profile")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Partially update own profile")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(summary="Update own profile")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Profiles"])
class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/user/profile/<pk>/  → any user profile
    PATCH /api/user/profile/<pk>/  → owner only
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)

    @extend_schema(summary="Retrieve a user profile by ID")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update profile (owner only)"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Update profile (owner only)"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.prefetch_related(
            "followers", "following"
        )


@extend_schema(tags=["Profiles"])
class UserListView(generics.ListAPIView):
    """
    GET /api/user/profile/?search=<term>
    Searches username and email fields.
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ("username", "email")

    @extend_schema(
        summary="Search users by username or email",
        parameters=[
            OpenApiParameter(
                name="search",
                description=(
                    "Search term matched against "
                    "username and email."
                ),
                required=False,
                type=str,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.prefetch_related(
            "followers", "following"
        )


@extend_schema(tags=["Relationships"])
class FollowView(APIView):
    """POST /api/user/<pk>/follow/"""
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Follow a user",
        description=(
            "Authenticated user follows the target user. "
            "Returns 400 if already following or "
            "attempting to follow self."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                },
            },
        },
    )
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        if target == request.user:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.following.filter(
            pk=target.pk
        ).exists():
            return Response(
                {"detail": "Already following this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.following.add(target)
        return Response(
            {"detail": f"Now following {target.username}."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Relationships"])
class UnfollowView(APIView):
    """POST /api/user/<pk>/unfollow/"""
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Unfollow a user",
        description=(
            "Authenticated user unfollows the target user. "
            "Returns 400 if not currently following."
        ),
        responses={
            200: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"}
                },
            }
        },
    )
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        if not request.user.following.filter(
            pk=target.pk
        ).exists():
            return Response(
                {
                    "detail": (
                        "You are not following this user."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.following.remove(target)
        return Response(
            {"detail": f"Unfollowed {target.username}."},
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        summary="List followers of a user",
        tags=["Relationships"],
    )
)
class FollowersListView(generics.ListAPIView):
    """GET /api/user/<pk>/followers/"""
    serializer_class = FollowSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        target = get_object_or_404(
            User, pk=self.kwargs["pk"]
        )
        return target.followers.prefetch_related(
            "followers", "following"
        )


@extend_schema_view(
    get=extend_schema(
        summary="List users followed by a user",
        tags=["Relationships"],
    )
)
class FollowingListView(generics.ListAPIView):
    """GET /api/user/<pk>/following/"""
    serializer_class = FollowSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        target = get_object_or_404(
            User, pk=self.kwargs["pk"]
        )
        return target.following.prefetch_related(
            "followers", "following"
        )
