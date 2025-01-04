from django.urls import path, include
from rest_framework.routers import DefaultRouter
from selection.views import ApplicantViewSet, CriteriaViewSet, RankingView, AuthViewSet
from django.contrib import admin
from django.http import JsonResponse

router = DefaultRouter()
router.register(r'applicants', ApplicantViewSet)
router.register(r'criteria', CriteriaViewSet)
# router.register(r'ranking', RankingView)
router.register(r'auth', AuthViewSet, basename='auth')

# 
#router tu ada base namenya kah? ada lah iya

def rak_ono(request):
    return JsonResponse({
        "error": "Not found",
        "status_code": 404
    }, status=404)


urlpatterns = [
    path('', rak_ono),
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/ranking/', RankingView.as_view()),
    # path('api/auth/', include('selection.auth_views'), name='ran'),
]