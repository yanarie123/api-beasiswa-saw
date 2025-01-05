from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.timezone import now, timedelta
from django.core.exceptions import ValidationError


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

    # Tambahan untuk OTP
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    # Metode untuk membuat OTP
    def generate_otp(self):
        import random
        self.otp_code = str(random.randint(100000, 999999))  # Kode 6 digit
        self.otp_expires_at = now() + timedelta(minutes=10)  # Kadaluarsa 10 menit
        self.save()


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
    average_score = models.FloatField(null=True, blank=True)
    parent_income = models.FloatField(null=True, blank=True)
    dependents = models.IntegerField(null=True, blank=True)
    decent_house = models.IntegerField(choices=DECENT_HOUSE_CHOICE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.name if self.user else "No User"


    def get_decent_house_display(self):
        return dict(self.DECENT_HOUSE_CHOICE).get(self.decent_house, "Unknown")


class Criteria(models.Model):
    name = models.CharField(max_length=100)
    weight = models.FloatField()
    is_benefit = models.BooleanField(default=True)

    def clean(self):
        if self.weight <= 0:
            raise ValidationError("Weight must be greater than 0.")

    def __str__(self):
        return self.name
