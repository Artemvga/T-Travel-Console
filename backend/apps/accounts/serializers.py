from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    def validate_username(self, value):
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError("Введите логин.")
        if User.objects.filter(username__iexact=normalized).exists():
            raise serializers.ValidationError("Такой логин уже существует.")
        return normalized

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Пароли должны совпадать."}
            )
        return attrs


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError("Введите логин.")
        return normalized

