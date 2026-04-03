from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .permissions import IsAdminRole
from .serializers import (
    UserAdminSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Public endpoint — register a new user (default role: viewer)."""

    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserProfileSerializer(user).data, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Return or update the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """Admin only — list all users."""

    permission_classes = [IsAdminRole]
    serializer_class = UserAdminSerializer
    queryset = User.objects.all().order_by('id')
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active']


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin only — retrieve, update, or deactivate a user."""

    permission_classes = [IsAdminRole]
    serializer_class = UserAdminSerializer
    queryset = User.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {'detail': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response(
            {'detail': 'User deactivated successfully.'},
            status=status.HTTP_200_OK,
        )
