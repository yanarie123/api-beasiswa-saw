from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    
    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Applicant(models.Model):
    DECENT_HOUSE_CHOICE = [
        (1, "Sangat Layak"),
        (2, "Layak"),
        (3, "Cukup Layak"),
        (4, "Kurang Layak"),
        (5, "Tidak Layak"),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="applicant",
        null=True,
        blank=True
    )
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=255)
    average_score = models.FloatField(null=True, blank=True)
    parent_income = models.FloatField(null=True, blank=True)
    dependents = models.IntegerField(null=True, blank=True)
    decent_house = models.IntegerField(choices=DECENT_HOUSE_CHOICE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Criteria(models.Model):
    name = models.CharField(max_length=100)
    weight = models.FloatField()
    is_benefit = models.BooleanField(default=True)
