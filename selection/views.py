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
        applicant, created = Applicant.objects.get_or_create(user=request.user)
        
        # Update data jika applicant sudah ada
        serializer = self.get_serializer(applicant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
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
            Applicant.objects.create(user=user)
            refresh = RefreshToken.for_user(user)
            return Response({
                "status": True,
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
                "status": False,
                "error": "Please provide both email and password"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Cek apakah user ada
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "status": False,
                "error": "No user found with this email"
            }, status=status.HTTP_200_OK)

        # Autentikasi password
        user = authenticate(email=email, password=password)
        
        if user:
            refresh = RefreshToken.for_user(user)
            
            # Default applicant_data = None
            applicant_data = None
            
            try:
                applicant = user.applicant
                
                # ----- [Mulai] Tambahan logika untuk mengecek data SAW tidak null dan hitung score -----
                # Pastikan kriteria yang ingin dihitung nilainya tidak `None`.
                # Misalkan: average_score, parent_income, dependents, decent_house (atau yang lain sesuai model)
                if (
                    applicant.average_score is not None and
                    applicant.parent_income is not None and
                    applicant.dependents is not None and
                    applicant.decent_house is not None
                ):
                    # Kita butuh semua applicant untuk mendapatkan nilai min dan max
                    all_applicants = Applicant.objects.all()
                    criteria = Criteria.objects.all()

                    # Siapkan dictionary untuk menampung min dan max tiap kriteria
                    max_values = {}
                    min_values = {}

                    for c in criteria:
                        # Ambil semua nilai kriteria c.name dari setiap applicant (yang tidak None)
                        values = [
                            getattr(a, c.name) for a in all_applicants
                            if getattr(a, c.name) is not None
                        ]
                        # Kalau values kosong, hindari ZeroDivisionError
                        if not values:
                            max_values[c.name] = 0
                            min_values[c.name] = 0
                        else:
                            max_values[c.name] = max(values)
                            min_values[c.name] = min(values)

                    # Lakukan normalisasi untuk applicant yang sedang login
                    total_score = 0
                    for c in criteria:
                        # Ambil nilai applicant saat ini
                        val = getattr(applicant, c.name, 0) or 0

                        # Hitung normalisasi
                        if c.is_benefit:
                            # val / max
                            if max_values[c.name] != 0:
                                norm = val / max_values[c.name]
                            else:
                                norm = 0
                        else:
                            # min / val
                            # Pastikan val != 0 untuk hindari ZeroDivisionError
                            if val != 0:
                                norm = min_values[c.name] / val
                            else:
                                norm = 0
                        
                        # Bobot kali nilai normalisasi
                        total_score += norm * c.weight
                    
                    saw_score = round(total_score, 4)
                else:
                    # Kalau data kriteria ada yang None, SAW tidak dihitung
                    saw_score = None
                # ----- [Selesai] Tambahan logika SAW -----

                applicant_data = {
                    "id": applicant.id,
                    "name": applicant.user.name,
                    "email": applicant.user.email,
                    "average_score": applicant.average_score,
                    "parent_income": applicant.parent_income,
                    "dependents": applicant.dependents,
                    "decent_house": applicant.get_decent_house_display(),
                    # Tampilkan score jika tidak None
                    "score": saw_score,
                }
            except Applicant.DoesNotExist:
                pass  # applicant_data tetap None

            return Response({
                "status": True,
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
            "status": False,
            "error": "Invalid credentials"
        }, status=status.HTTP_200_OK)

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

        # Filter out applicants with any null values in criteria
        valid_applicants = []
        for applicant in applicants:
            is_valid = True
            for criterion in criteria:
                value = getattr(applicant, criterion.name, None)
                if value is None:  # Skip if any value is null
                    is_valid = False
                    break
            if is_valid:
                valid_applicants.append(applicant)

        # Prepare normalized data
        normalized_data = []
        for applicant in valid_applicants:
            norm = []
            for criterion in criteria:
                values = [getattr(a, criterion.name, 0) for a in valid_applicants]
                value = getattr(applicant, criterion.name, 0)
                
                if criterion.is_benefit:
                    max_value = max(values) if max(values) > 0 else 1  # Avoid division by zero
                    norm.append(value / max_value)
                else:
                    min_value = min(values) if min(values) > 0 else 1  # Avoid division by zero
                    norm.append(min_value / value if value > 0 else 0)  # Handle zero value

            normalized_data.append(norm)

        # Calculate scores
        scores = []
        for norm in normalized_data:
            score = sum([n * c.weight for n, c in zip(norm, criteria)])
            scores.append(score)

        # Sort results
        results = sorted(zip(valid_applicants, scores), key=lambda x: x[1], reverse=True)

        # Prepare ranking response
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
                "score": round(score, 4),  # Rounded for better readability
            })

        return Response(ranking)



