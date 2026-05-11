import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DocumentoPrestador, HistoricoProcesso, PrestadorEmpresa, ProcessoHomologacao, TipoDocumento


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
        processo = ProcessoHomologacao.objects.get(prestador=prestador)

        self.assertEqual(user.perfil, get_user_model().Perfil.PRESTADOR)
        self.assertTrue(user.check_password('SenhaForte123'))
        self.assertNotEqual(user.password, 'SenhaForte123')
        self.assertEqual(prestador.cnpj, '12345678000190')
        self.assertEqual(processo.status, ProcessoHomologacao.Status.CADASTRO_INICIADO)
        self.assertTrue(processo.historico.filter(acao='Cadastro criado').exists())

    def test_register_prestador_rejects_invalid_cnpj_format(self):
        payload = {**self.payload, 'cnpj': '123'}

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cnpj', response.data)


class LoginTests(APITestCase):
    def test_login_returns_jwt_pair_and_user_session(self):
        get_user_model().objects.create_user(
            email='prestador@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
            first_name='Maria',
            last_name='Silva',
        )

        response = self.client.post(
            reverse('login'),
            {'email': 'prestador@example.com', 'senha': 'SenhaForte123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'prestador@example.com')
        self.assertEqual(response.data['user']['perfil'], get_user_model().Perfil.PRESTADOR)
        self.assertEqual(response.data['user']['nome'], 'Maria Silva')

    def test_me_returns_authenticated_user_session(self):
        user = get_user_model().objects.create_user(
            email='admin@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.ADMINISTRADOR,
        )
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(reverse('auth-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], user.id)
        self.assertEqual(response.data['email'], 'admin@example.com')
        self.assertEqual(response.data['perfil'], get_user_model().Perfil.ADMINISTRADOR)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentoUploadTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        media_root = cls._overridden_settings['MEDIA_ROOT']
        super().tearDownClass()
        shutil.rmtree(media_root, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='prestador-docs@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )
        self.prestador = PrestadorEmpresa.objects.create(
            user=self.user,
            razao_social='Clinica Docs LTDA',
            nome_fantasia='Clinica Docs',
            cnpj='98765432000110',
            endereco='Rua dos Documentos, 200',
            nome_responsavel='Joao Silva',
            email='prestador-docs@example.com',
            telefone='11999999999',
        )
        self.tipo_documento, _ = TipoDocumento.objects.get_or_create(nome='Contrato Social')
        self.url = reverse('documentos-upload')
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_upload_pdf_document(self):
        arquivo = SimpleUploadedFile(
            'contrato.pdf',
            b'%PDF-1.4 conteudo',
            content_type='application/pdf',
        )

        response = self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DocumentoPrestador.objects.count(), 1)
        documento = DocumentoPrestador.objects.get()

        self.assertEqual(documento.processo.prestador, self.prestador)
        self.assertTrue(HistoricoProcesso.objects.filter(processo=documento.processo, acao='Documento enviado').exists())
        self.assertEqual(response.data['documentos'][0]['tipo_documento']['id'], self.tipo_documento.id)

    def test_upload_rejects_non_pdf_file(self):
        arquivo = SimpleUploadedFile(
            'contrato.txt',
            b'conteudo',
            content_type='text/plain',
        )

        response = self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('arquivos', response.data)
        self.assertEqual(DocumentoPrestador.objects.count(), 0)

    def test_upload_rejects_file_with_pdf_content_type_but_invalid_payload(self):
        arquivo = SimpleUploadedFile(
            'contrato.pdf',
            b'conteudo falso',
            content_type='application/pdf',
        )

        response = self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('arquivos', response.data)
        self.assertEqual(DocumentoPrestador.objects.count(), 0)

    def test_upload_accepts_multiple_pdf_documents(self):
        tipo_documento_2, _ = TipoDocumento.objects.get_or_create(nome='Comprovante de Endereco')
        arquivo_1 = SimpleUploadedFile('contrato.pdf', b'%PDF-1.4 contrato', content_type='application/pdf')
        arquivo_2 = SimpleUploadedFile('endereco.pdf', b'%PDF-1.4 endereco', content_type='application/pdf')

        response = self.client.post(
            self.url,
            {
                'arquivos': [arquivo_1, arquivo_2],
                'tipos_documento': [str(self.tipo_documento.id), str(tipo_documento_2.id)],
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DocumentoPrestador.objects.count(), 2)
        self.assertEqual(len(response.data['documentos']), 2)

    def test_process_summary_returns_status_pending_documents_and_history(self):
        processo = ProcessoHomologacao.objects.create(prestador=self.prestador)
        processo.registrar_evento(acao='Cadastro criado', usuario=self.user)

        response = self.client.get(reverse('prestador-processo'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status_atual'], ProcessoHomologacao.Status.CADASTRO_INICIADO)
        self.assertGreaterEqual(len(response.data['pendencias']), 1)
        self.assertEqual(response.data['documentos_enviados'], [])
        self.assertEqual(response.data['historico'][0]['acao'], 'Cadastro criado')

    def test_upload_updates_process_to_validation_when_all_required_documents_are_sent(self):
        TipoDocumento.objects.filter(obrigatorio=True).exclude(id=self.tipo_documento.id).update(obrigatorio=False)
        arquivo = SimpleUploadedFile('contrato.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf')

        response = self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )

        processo = DocumentoPrestador.objects.get().processo

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(processo.status, ProcessoHomologacao.Status.EM_VALIDACAO)
        self.assertTrue(processo.historico.filter(acao='Status atualizado').exists())

    def test_list_active_document_types(self):
        TipoDocumento.objects.create(nome='Documento Inativo', ativo=False)

        response = self.client.get(reverse('documentos-tipos'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nomes = {tipo['nome'] for tipo in response.data['tipos_documento']}

        self.assertIn('Contrato Social', nomes)
        self.assertNotIn('Documento Inativo', nomes)
