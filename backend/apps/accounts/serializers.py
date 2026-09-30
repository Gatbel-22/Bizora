from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.businesses.models import BusinessType
from apps.businesses.serializers import MembershipSummarySerializer
from apps.businesses.services import get_active_memberships
from apps.core.money import CURRENCY_CHOICES, DEFAULT_CURRENCY

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone", "created_at")
        read_only_fields = ("id", "email", "created_at")


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    business_name = serializers.CharField(max_length=150)
    business_type = serializers.ChoiceField(
        choices=BusinessType.choices, default=BusinessType.OTHER
    )
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, default=DEFAULT_CURRENCY)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(TokenObtainPairSerializer):
    """Standard JWT login, plus the user and the businesses they belong to."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        data["memberships"] = MembershipSummarySerializer(
            get_active_memberships(self.user), many=True
        ).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value
