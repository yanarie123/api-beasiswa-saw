from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Applicant, Criteria
from .serializers import ApplicantSerializer, CriteriaSerializer, UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import now

class ApplicantViewSet(viewsets.ModelViewSet):
    # queryset = Applicant.objects.select_related('user').all()
    serializer_class = ApplicantSerializer

    def get_queryset(self):
        return Applicant.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        if hasattr(request.user, "applicant"):
            return Response(
                {"error": "Applicant already exists for this user"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            app = serializer.save()
            response_data = app.daya
            response_data["id"] = app.id
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        applicant = self.get_object()
        if applicant.user != request.user:
            return Response(
                {"error": "You are not allowed to update this applicant"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    

class CriteriaViewSet(viewsets.ModelViewSet):
    queryset = Criteria.objects.all()
    serializer_class = CriteriaSerializer


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=["post"])
    def register(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Create associated Applicant
            Applicant.objects.create(user=user)  # Menghapus field redundan
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Registration successful",
                "user": serializer.data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def login(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({
                "error": "Please provide both email and password"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "error": "No user found with this email"
            }, status=status.HTTP_404_NOT_FOUND)

        user = authenticate(email=email, password=password)
        
        if user:
            refresh = RefreshToken.for_user(user)
            try:
                applicant = user.applicant
                applicant_data = {
                    "id": applicant.id,
                    "name": applicant.user.name,
                    "email": applicant.user.email,
                    "average_score": applicant.average_score,
                    "parent_income": applicant.parent_income,
                    "dependents": applicant.dependents,
                    "decent_house": applicant.get_decent_house_display(),
                }
            except (Applicant.DoesNotExist, Exception):
                applicant_data = None

            return Response({
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                },
                "applicant": applicant_data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            })
        
        return Response({
            "error": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=["post"])
    def forgot_password(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate OTP dan kirim melalui email
        user.generate_otp()
        try:
            send_mail(
                subject="Your Password Reset OTP Code",
                message=f"Use this OTP code to reset your password: {user.otp_code}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to send email. Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"message": "OTP has been sent to your email."})

    @action(detail=False, methods=["post"])
    def reset_password(self, request):
        email = request.data.get("email")
        otp_code = request.data.get("otp_code")
        new_password = request.data.get("new_password")

        if not email or not otp_code or not new_password:
            return Response(
                {"error": "All fields (email, otp_code, new_password) are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)

            if user.otp_code != otp_code:
                return Response(
                    {"error": "Invalid OTP code."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if user.otp_expires_at < now():
                return Response(
                    {"error": "OTP code has expired."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.otp_code = None
            user.otp_expires_at = None
            user.save()

            return Response({"message": "Password has been reset successfully."})

        except User.DoesNotExist:
            return Response(
                {"error": "User does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )


class RankingView(APIView):
    def get(self, request):
        applicants = Applicant.objects.select_related('user').all()
        criteria = Criteria.objects.all()

        normalized_data = []
        for applicant in applicants:
            norm = []
            for criterion in criteria:
                value = getattr(applicant, criterion.name, 0)
                if criterion.is_benefit:
                    norm.append(value / max([getattr(a, criterion.name, 0) for a in applicants]))
                else:
                    norm.append(min([getattr(a, criterion.name, 0) for a in applicants]) / value)
            normalized_data.append(norm)

        scores = []
        for norm in normalized_data:
            score = sum([n * c.weight for n, c in zip(norm, criteria)])
            scores.append(score)

        results = sorted(zip(applicants, scores), key=lambda x: x[1], reverse=True)

        ranking = []
        for index, (applicant, score) in enumerate(results, 1):
            ranking.append({
                "rank": index,
                "name": applicant.user.name,
                "email": applicant.user.email,
                "average_score": applicant.average_score,
                "parent_income": applicant.parent_income,
                "dependents": applicant.dependents,
                "decent_house": applicant.get_decent_house_display(),
                "score": score,
            })

        return Response(ranking)
