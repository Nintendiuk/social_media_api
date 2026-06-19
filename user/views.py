from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
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


# Auth views
@extend_schema(tags=["Auth"])
class RegisterView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Register a new user",
        request=UserRegistrationSerializer,
        responses={201: UserRegistrationSerializer},
        examples=[
            OpenApiExample(
                "Example",
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
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth"])
class LoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Obtain JWT token pair",
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
                "Example",
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
        if not serializer.is_valid():
            return Response({"detail": "Invalid email or password"},
                            status=status.HTTP_401_UNAUTHORIZED)
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
        request=LogoutSerializer,
        responses={205: None},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            status=status.HTTP_205_RESET_CONTENT
        )


# ── User ViewSet ──────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="Search users",
        tags=["Profiles"],
        parameters=[
            OpenApiParameter(
                name="search",
                description=(
                    "Match against username or email."
                ),
                required=False,
                type=str,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a user profile",
        tags=["Profiles"],
    ),
    partial_update=extend_schema(
        summary="Update own profile",
        tags=["Profiles"],
    ),
    me=extend_schema(
        summary="Retrieve or update own profile",
        tags=["Profiles"],
    ),
    follow=extend_schema(
        summary="Follow a user",
        tags=["Relationships"],
    ),
    unfollow=extend_schema(
        summary="Unfollow a user",
        tags=["Relationships"],
    ),
    followers=extend_schema(
        summary="List followers",
        tags=["Relationships"],
    ),
    following=extend_schema(
        summary="List following",
        tags=["Relationships"],
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ("username", "email")
    http_method_names = [
        "get", "post", "patch", "put",
        "delete", "head", "options",
    ]

    def get_queryset(self):
        return User.objects.prefetch_related(
            "followers", "following"
        )

    def get_permissions(self):
        if self.action in (
            "partial_update", "update", "destroy"
        ):
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

    # ── private helpers ───────────────────────────────

    def _follow_response(self, target, action):
        is_following = self.request.user.following.filter(
            pk=target.pk
        ).exists()

        if action == "follow":
            if target == self.request.user:
                return Response(
                    {
                        "detail": (
                            "You cannot follow yourself."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if is_following:
                return Response(
                    {"detail": "Already following."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            self.request.user.following.add(target)
            return Response(
                {
                    "detail": (
                        f"Now following {target.username}."
                    )
                },
                status=status.HTTP_200_OK,
            )

        if not is_following:
            return Response(
                {
                    "detail": (
                        "You are not following this user."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.request.user.following.remove(target)
        return Response(
            {"detail": f"Unfollowed {target.username}."},
            status=status.HTTP_200_OK,
        )

    def _follow_list_response(self, relation):
        target = self.get_object()
        qs = getattr(target, relation).prefetch_related(
            "followers", "following"
        )
        serializer = FollowSerializer(
            qs,
            many=True,
            context={"request": self.request},
        )
        return Response(serializer.data)

    # ── actions ───────────────────────────────────────

    @action(
        detail=False,
        methods=["get", "patch", "put"],
        url_path="me",
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        if request.method == "GET":
            return Response(
                self.get_serializer(request.user).data
            )
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def follow(self, request, pk=None):
        return self._follow_response(
            self.get_object(), "follow"
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def unfollow(self, request, pk=None):
        return self._follow_response(
            self.get_object(), "unfollow"
        )

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAuthenticated],
    )
    def followers(self, request, pk=None):
        return self._follow_list_response("followers")

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[IsAuthenticated],
    )
    def following(self, request, pk=None):
        return self._follow_list_response("following")
