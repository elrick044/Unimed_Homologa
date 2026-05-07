from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PrestadorEmpresa


class PrestadorRegisterTests(APITestCase):
    def setUp(self):
        self.url = reverse('prestador-register')
        self.payload = {
            'razao_social': 'Clinica Exemplo LTDA',
            'nome_fantasia': 'Clinica Exemplo',
            'cnpj': '12.345.678/0001-90',
            'endereco': 'Rua Central, 100',
            'nome_responsavel': 'Maria Silva',
            'email': 'prestador@example.com',
            'telefone': '(11) 99999-9999',
            'senha': 'SenhaForte123',
        }

    def test_register_prestador_creates_user_with_hashed_password(self):
        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email='prestador@example.com')
        prestador = PrestadorEmpresa.objects.get(user=user)

        self.assertEqual(user.perfil, get_user_model().Perfil.PRESTADOR)
        self.assertTrue(user.check_password('SenhaForte123'))
        self.assertNotEqual(user.password, 'SenhaForte123')
        self.assertEqual(prestador.cnpj, '12345678000190')

    def test_register_prestador_rejects_invalid_cnpj_format(self):
        payload = {**self.payload, 'cnpj': '123'}

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cnpj', response.data)


class LoginTests(APITestCase):
    def test_login_returns_jwt_pair(self):
        get_user_model().objects.create_user(
            email='prestador@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )

        response = self.client.post(
            reverse('login'),
            {'email': 'prestador@example.com', 'senha': 'SenhaForte123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
