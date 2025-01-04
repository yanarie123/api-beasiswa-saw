from rest_framework import serializers
from .models import Applicant, Criteria
from django.contrib.auth import get_user_model, authenticate

User = get_user_model()

class ApplicantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = '__all__'

class CriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criteria
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ("id", "email", "password", "name")
        extra_kwargs = {
            "password": {"write_only": True}
        }
        
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data.get("name", "")
        )
        return user