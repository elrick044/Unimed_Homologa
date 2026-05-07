from django.urls import path

from .views import LoginView, PrestadorRegisterView

urlpatterns = [
    path('auth/register/prestador/', PrestadorRegisterView.as_view(), name='prestador-register'),
    path('auth/login/', LoginView.as_view(), name='login'),
]
