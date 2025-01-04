from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Applicant, Criteria
from .serializers import ApplicantSerializer, CriteriaSerializer, UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from .models import User, Applicant
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings

class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer


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
            Applicant.objects.create(
                user=user, # --< Ini dpet dari mana variabelnya joy?
                name=user.name,
                email=user.email
            )
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
                    "name": applicant.name,
                    "email": applicant.email,
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
                {"error": "User with this email does not exist"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create reset password link
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
        
        # Send email
        send_mail(
            subject="Reset Your Password",
            message=f"Click the following link to reset your password: {reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return Response({"message": "Password reset email has been sent"})

    @action(detail=False, methods=["post"])
    def reset_password(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("new_password")
        
        if not uid or not token or not new_password:
            return Response(
                {"error": "Missing required fields"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({"message": "Password has been reset successfully"})
            else:
                return Response(
                    {"error": "Invalid or expired token"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (TypeError, ValueError, User.DoesNotExist):
            return Response(
                {"error": "Invalid reset link"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class RankingView(APIView):
    def get(self, request):
        # Mengambil data pendaftar dan kriteriaz
        applicants = Applicant.objects.all()
        criteria = Criteria.objects.all()

        # Normalisasi data
        normalized_data = []
        for applicant in applicants:
            norm = []
            for criterion in criteria:
                # Ambil nilai dari atribut dinamis
                value = getattr(applicant, criterion.name)

                # Normalisasi untuk Benefit
                if criterion.is_benefit:
                    norm.append(value / max([getattr(a, criterion.name) for a in applicants]))
                # Normalisasi untuk Cost
                else:
                    norm.append(min([getattr(a, criterion.name) for a in applicants]) / value)
            normalized_data.append(norm)

        # Menghitung skor
        scores = []
        for norm in normalized_data:
            score = sum([n * c.weight for n, c in zip(norm, criteria)])
            scores.append(score)

        # Mengurutkan hasil
        results = sorted(zip(applicants, scores), key=lambda x: x[1], reverse=True)

        # Format hasil
        ranking = []
        for index, (applicant, score) in enumerate(results, 1):
            ranking.append({
                "rank": index,
                "name": applicant.name,
                "email": applicant.email,
                "average_score": applicant.average_score,
                "parent_income": applicant.parent_income,
                "dependents": applicant.dependents,
                "decent_house": dict(Applicant._meta.get_field('decent_house').choices)[applicant.decent_house],
                "score": score,
            })

        return Response(ranking)
