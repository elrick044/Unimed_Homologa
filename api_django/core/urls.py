from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminConfigDocumentoDetailView,
    AdminConfigDocumentoListCreateView,
    AdminConfigFluxoDetailView,
    AdminConfigFluxoListCreateView,
    AdminConfigUsuarioDetailView,
    AdminConfigUsuarioListCreateView,
    AdminDocumentoValidacaoView,
    AdminProcessoDetailView,
    AdminProcessoParecerView,
    AdminProcessoListView,
    DocumentoUploadView,
    LoginView,
    MeView,
    ProcessoDocumentoListView,
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
    path('processos/<int:id_processo>/documentos/', ProcessoDocumentoListView.as_view(), name='processo-documentos'),
    path('admin/processos/', AdminProcessoListView.as_view(), name='admin-processos'),
    path('admin/processos/<int:id_processo>/', AdminProcessoDetailView.as_view(), name='admin-processo-detail'),
    path('admin/processos/<int:id_processo>/parecer/', AdminProcessoParecerView.as_view(), name='admin-processo-parecer'),
    path('admin/documentos/<int:id_documento>/validar/', AdminDocumentoValidacaoView.as_view(), name='admin-documento-validar'),
    path('admin/config/usuarios/', AdminConfigUsuarioListCreateView.as_view(), name='admin-config-usuarios'),
    path('admin/config/usuarios/<int:id_usuario>/', AdminConfigUsuarioDetailView.as_view(), name='admin-config-usuario-detail'),
    path('admin/config/documentos/', AdminConfigDocumentoListCreateView.as_view(), name='admin-config-documentos'),
    path('admin/config/documentos/<int:id_tipo_documento>/', AdminConfigDocumentoDetailView.as_view(), name='admin-config-documento-detail'),
    path('admin/config/fluxos/', AdminConfigFluxoListCreateView.as_view(), name='admin-config-fluxos'),
    path('admin/config/fluxos/<int:id_fluxo>/', AdminConfigFluxoDetailView.as_view(), name='admin-config-fluxo-detail'),
]
