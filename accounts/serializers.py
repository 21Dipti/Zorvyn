from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email',
            'first_name', 'last_name',
            'password', 'password_confirm',
        )
        read_only_fields = ('id',)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email',
            'first_name', 'last_name',
            'role', 'date_joined', 'last_login',
        )
        read_only_fields = ('id', 'username', 'role', 'date_joined', 'last_login')


class UserAdminSerializer(serializers.ModelSerializer):
    """Full serializer for admin-level user management."""

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email',
            'first_name', 'last_name',
            'role', 'is_active',
            'date_joined', 'last_login',
        )
        read_only_fields = ('id', 'username', 'date_joined', 'last_login')

    def validate_role(self, value):
        valid_roles = [r[0] for r in User.ROLE_CHOICES]
        if value not in valid_roles:
            raise serializers.ValidationError(f'Role must be one of: {", ".join(valid_roles)}.')
        return value
