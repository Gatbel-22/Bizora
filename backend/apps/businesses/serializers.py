from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Business, BusinessMembership, Role

User = get_user_model()

MAX_LOGO_BYTES = 2 * 1024 * 1024


class BusinessSerializer(serializers.ModelSerializer):
    profile_complete = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = (
            "id",
            "name",
            "business_type",
            "owner_name",
            "phone",
            "email",
            "address",
            "country",
            "currency",
            "tax_name",
            "default_tax_rate",
            "logo",
            "date_format",
            "timezone",
            "profile_complete",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_profile_complete(self, obj):
        return bool(obj.address and obj.phone)

    def validate_logo(self, value):
        if value and value.size > MAX_LOGO_BYTES:
            raise serializers.ValidationError("Logo must be smaller than 2 MB.")
        return value


class MembershipSummarySerializer(serializers.ModelSerializer):
    """Compact view used at login: which businesses can this user act for?"""

    business_id = serializers.UUIDField(source="business.id", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    currency = serializers.CharField(source="business.currency", read_only=True)

    class Meta:
        model = BusinessMembership
        fields = ("id", "business_id", "business_name", "currency", "role")


class MemberUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone")


class MembershipSerializer(serializers.ModelSerializer):
    user = MemberUserSerializer(read_only=True)

    class Meta:
        model = BusinessMembership
        fields = ("id", "user", "role", "is_active", "created_at")


class MembershipCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=[(Role.MANAGER, "Manager"), (Role.STAFF, "Staff")])

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value


class MembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMembership
        fields = ("role", "is_active")

    def validate_role(self, value):
        if value == Role.OWNER:
            raise serializers.ValidationError("A member can't be made an owner.")
        return value
