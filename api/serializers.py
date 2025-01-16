from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import User, Subscription


# User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


# Register Serializer
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Instead of manual object creation, use super()
        user = super().create(validated_data)
        user.set_password(validated_data['password'])  # Ensure password is hashed
        user.save()
        return user

    # Optional: Add a custom password validation function
    def validate_password(self, value):
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return value


# Subscription Serializer
class SubscriptionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Nested UserSerializer to include user details
    time_left = serializers.ReadOnlyField()

    class Meta:
        model = Subscription
        fields = ['id', 'user', 'membership_type', 'purchase_date', 'start_date', 'end_date', 'time_left']
