from django.urls import path

from .views import DocumentoUploadView, LoginView, PrestadorRegisterView, TipoDocumentoListView

urlpatterns = [
    path('auth/register/prestador/', PrestadorRegisterView.as_view(), name='prestador-register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('documentos/tipos/', TipoDocumentoListView.as_view(), name='documentos-tipos'),
    path('documentos/upload/', DocumentoUploadView.as_view(), name='documentos-upload'),
]
