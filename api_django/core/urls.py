from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    DocumentoUploadView,
    LoginView,
    MeView,
    PrestadorProcessoView,
    PrestadorRegisterView,
    TipoDocumentoListView,
)

urlpatterns = [
    path('auth/register/prestador/', PrestadorRegisterView.as_view(), name='prestador-register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('documentos/tipos/', TipoDocumentoListView.as_view(), name='documentos-tipos'),
    path('documentos/upload/', DocumentoUploadView.as_view(), name='documentos-upload'),
    path('prestador/processo/', PrestadorProcessoView.as_view(), name='prestador-processo'),
]
