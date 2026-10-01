from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Role, RoleCode, User


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "code", "name", "description")


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    roles = serializers.ListField(
        source="role_codes", child=serializers.CharField(), read_only=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "roles",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices), allow_empty=False
    )

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "roles", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def to_representation(self, instance):
        return UserSerializer(instance).data


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "is_active")

    def to_representation(self, instance):
        return UserSerializer(instance).data


class UserRolesUpdateSerializer(serializers.Serializer):
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=RoleCode.choices), allow_empty=False
    )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """What any signed-in user may change about themselves."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone")

    def to_representation(self, instance):
        return UserSerializer(instance).data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


class PatientRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True, default="")
    phone = serializers.CharField(max_length=20, allow_blank=True, default="")
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=["MALE", "FEMALE", "OTHER", "UNDISCLOSED"], default="UNDISCLOSED"
    )
    city = serializers.CharField(max_length=150, allow_blank=True, default="")
    consent_given = serializers.BooleanField()
    whatsapp_opt_in = serializers.BooleanField(default=False)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_consent_given(self, value):
        if not value:
            raise serializers.ValidationError("Consent is required to create an account.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs["email"], first_name=attrs["first_name"])
        validate_password(attrs["password"], candidate)
        return attrs
