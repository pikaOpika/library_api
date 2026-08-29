from rest_framework import serializers

from django.contrib.auth import get_user_model

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email", "first_name", "last_name", "password", "is_staff"]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 8,
                "style": {"input_type": "password"},
            },
            "is_staff": {
                "read_only": True,
            }
        }

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class UserRegisterSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ["email", "password"]


class UserProfileUpdateSerializer(UserRegisterSerializer):
    class Meta(UserRegisterSerializer.Meta):
        fields = ["email", "first_name", "last_name"]
