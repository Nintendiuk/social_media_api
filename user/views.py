from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from user.models import User
from user.permissions import IsOwnerOrReadOnly
from user.serializers import UserProfileSerializer

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from user.serializers import (
    LoginSerializer,
    LogoutSerializer,
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
