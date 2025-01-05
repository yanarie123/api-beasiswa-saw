from rest_framework import serializers
from .models import Applicant, Criteria
from django.contrib.auth import get_user_model

User = get_user_model()

class ApplicantSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    decent_house_display = serializers.CharField(source="get_decent_house_display", read_only=True)

    class Meta:
        model = Applicant
        fields = [
            "id",
            "name",
            "email",
            "average_score",
            "parent_income",
            "dependents",
            "decent_house",
            "decent_house_display",
            "created_at",
            "updated_at",
        ]
    
    def validate(self, data):
        # Validate all fields in one pass
        errors = {}
        
        average_score = data.get("average_score")
        if average_score is not None and (average_score < 0 or average_score > 100):
            errors["average_score"] = "Average score must be between 0 and 100."
            
        parent_income = data.get("parent_income") 
        if parent_income is not None and parent_income < 0:
            errors["parent_income"] = "Parent income must be greater than 0."
            
        dependents = data.get("dependents")
        if dependents is not None and dependents < 0:
            errors["dependents"] = "Dependents must be greater than 0."
            
        if errors:
            raise serializers.ValidationError(errors)
            
        return data


class CriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criteria
        fields = ["id", "name", "weight", "is_benefit"]

    def validate_weight(self, value):
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0.")
        return value


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("id", "email", "password", "confirm_password", "name")
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")  # Remove confirm_password
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data.get("name", "")
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
