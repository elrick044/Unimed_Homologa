import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    ConfiguracaoFluxoPadrao,
    DocumentoPrestador,
    EtapaConfiguracaoPadrao,
    EtapaAprovacao,
    FluxoAprovacao,
    HistoricoProcesso,
    ParecerProcesso,
    PrestadorEmpresa,
    ProcessoHomologacao,
    TipoDocumento,
)


def auth_client(client, user):
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


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


class AdminConfigTests(APITestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            email='system-admin@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.ADMINISTRADOR,
        )
        auth_client(self.client, self.admin_user)

    def test_prestador_cannot_access_config_routes(self):
        prestador_user = get_user_model().objects.create_user(
            email='config-prestador@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )
        auth_client(self.client, prestador_user)

        response = self.client.get(reverse('admin-config-usuarios'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrative_team_cannot_access_config_routes(self):
        equipe_user = get_user_model().objects.create_user(
            email='config-equipe@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        auth_client(self.client, equipe_user)

        response = self.client.get(reverse('admin-config-documentos'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_system_admin_can_manage_internal_users(self):
        create_response = self.client.post(
            reverse('admin-config-usuarios'),
            {
                'email': 'nova-equipe@example.com',
                'perfil': get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
                'first_name': 'Nova',
                'last_name': 'Equipe',
                'is_active': True,
                'password': 'SenhaForte123',
            },
            format='json',
        )
        user_id = create_response.data['id']

        update_response = self.client.put(
            reverse('admin-config-usuario-detail', kwargs={'id_usuario': user_id}),
            {'first_name': 'Analista'},
            format='json',
        )
        delete_response = self.client.delete(
            reverse('admin-config-usuario-detail', kwargs={'id_usuario': user_id}),
        )

        user = get_user_model().objects.get(id=user_id)

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['first_name'], 'Analista')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(user.is_active)

    def test_system_admin_cannot_create_prestador_on_internal_user_route(self):
        response = self.client.post(
            reverse('admin-config-usuarios'),
            {
                'email': 'prestador-interno@example.com',
                'perfil': get_user_model().Perfil.PRESTADOR,
                'is_active': True,
                'password': 'SenhaForte123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('perfil', response.data)

    def test_document_type_delete_is_soft_delete_and_keeps_documents(self):
        tipo = TipoDocumento.objects.create(nome='Documento Critico', obrigatorio=True, ativo=True)
        prestador_user = get_user_model().objects.create_user(
            email='doc-config-prestador@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )
        prestador = PrestadorEmpresa.objects.create(
            user=prestador_user,
            razao_social='Config Docs LTDA',
            nome_fantasia='Config Docs',
            cnpj='33333333000193',
            endereco='Rua D, 500',
            nome_responsavel='Daniel Rocha',
            email='doc-config-prestador@example.com',
            telefone='11666666666',
        )
        processo = ProcessoHomologacao.objects.create(prestador=prestador)
        DocumentoPrestador.objects.create(
            prestador=prestador,
            processo=processo,
            tipo_documento=tipo,
            arquivo='documentos/critico.pdf',
            content_type='application/pdf',
            tamanho_bytes=100,
        )

        response = self.client.delete(reverse('admin-config-documento-detail', kwargs={'id_tipo_documento': tipo.id}))

        tipo.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(tipo.ativo)
        self.assertEqual(DocumentoPrestador.objects.filter(tipo_documento=tipo).count(), 1)

    def test_system_admin_can_manage_document_types(self):
        create_response = self.client.post(
            reverse('admin-config-documentos'),
            {'nome': 'Licenca Sanitaria', 'descricao': 'Licenca atualizada.', 'obrigatorio': True, 'ativo': True},
            format='json',
        )

        update_response = self.client.put(
            reverse('admin-config-documento-detail', kwargs={'id_tipo_documento': create_response.data['id']}),
            {'obrigatorio': False},
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertFalse(update_response.data['obrigatorio'])

    def test_system_admin_can_configure_default_approval_flow_order(self):
        aprovador_1 = get_user_model().objects.create_user(
            email='config-aprovador-1@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        aprovador_2 = get_user_model().objects.create_user(
            email='config-aprovador-2@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )

        response = self.client.post(
            reverse('admin-config-fluxos'),
            {
                'nome': 'Fluxo Padrao Assistencial',
                'ativo': True,
                'etapas': [
                    {'aprovador': aprovador_2.id, 'ordem': 1},
                    {'aprovador': aprovador_1.id, 'ordem': 2},
                ],
            },
            format='json',
        )

        configuracao = ConfiguracaoFluxoPadrao.objects.get(id=response.data['id'])
        etapas = list(configuracao.etapas.order_by('ordem'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(etapas[0].aprovador, aprovador_2)
        self.assertEqual(etapas[1].aprovador, aprovador_1)

    def test_active_flow_config_drives_generated_approval_chain(self):
        aprovador_1 = get_user_model().objects.create_user(
            email='config-chain-1@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        aprovador_2 = get_user_model().objects.create_user(
            email='config-chain-2@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        configuracao = ConfiguracaoFluxoPadrao.objects.create(nome='Fluxo Ativo', ativo=True)
        EtapaConfiguracaoPadrao.objects.create(configuracao=configuracao, aprovador=aprovador_2, ordem=1)
        EtapaConfiguracaoPadrao.objects.create(configuracao=configuracao, aprovador=aprovador_1, ordem=2)
        prestador_user = get_user_model().objects.create_user(
            email='config-chain-prestador@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )
        prestador = PrestadorEmpresa.objects.create(
            user=prestador_user,
            razao_social='Config Chain LTDA',
            nome_fantasia='Config Chain',
            cnpj='44444444000194',
            endereco='Rua E, 600',
            nome_responsavel='Elaine Moraes',
            email='config-chain-prestador@example.com',
            telefone='11555555555',
        )

        processo = ProcessoHomologacao.objects.create(
            prestador=prestador,
            status=ProcessoHomologacao.Status.EM_APROVACAO_INTERNA,
        )
        etapas = list(processo.fluxo_aprovacao.etapas.order_by('ordem'))

        self.assertEqual(etapas[0].aprovador, aprovador_2)
        self.assertEqual(etapas[1].aprovador, aprovador_1)


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
        self.assertEqual(documento.status, DocumentoPrestador.Status.ENVIADO)
        self.assertEqual(documento.versao, 1)
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

    def test_upload_same_document_type_creates_new_version_and_substitutes_previous(self):
        arquivo_1 = SimpleUploadedFile('contrato-v1.pdf', b'%PDF-1.4 v1', content_type='application/pdf')
        arquivo_2 = SimpleUploadedFile('contrato-v2.pdf', b'%PDF-1.4 v2', content_type='application/pdf')

        self.client.post(
            self.url,
            {'arquivo': arquivo_1, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )
        response = self.client.post(
            self.url,
            {'arquivo': arquivo_2, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )

        documentos = DocumentoPrestador.objects.order_by('versao')
        documento_v1 = documentos[0]
        documento_v2 = documentos[1]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DocumentoPrestador.objects.count(), 2)
        self.assertEqual(documento_v1.status, DocumentoPrestador.Status.SUBSTITUIDO)
        self.assertEqual(documento_v2.status, DocumentoPrestador.Status.ENVIADO)
        self.assertEqual(documento_v2.versao, 2)
        self.assertEqual(documento_v2.documento_anterior, documento_v1)
        self.assertTrue(documento_v2.processo.historico.filter(acao='Documento substituido').exists())

    def test_process_document_list_returns_version_history(self):
        arquivo_1 = SimpleUploadedFile('contrato-v1.pdf', b'%PDF-1.4 v1', content_type='application/pdf')
        arquivo_2 = SimpleUploadedFile('contrato-v2.pdf', b'%PDF-1.4 v2', content_type='application/pdf')

        self.client.post(
            self.url,
            {'arquivo': arquivo_1, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )
        self.client.post(
            self.url,
            {'arquivo': arquivo_2, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )
        processo = ProcessoHomologacao.objects.get(prestador=self.prestador)

        response = self.client.get(reverse('processo-documentos', kwargs={'id_processo': processo.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['documentos']), 1)
        self.assertEqual(response.data['documentos'][0]['documento_atual']['versao'], 2)
        self.assertEqual(len(response.data['documentos'][0]['versoes']), 2)

    def test_process_document_list_blocks_other_prestador(self):
        outro_user = get_user_model().objects.create_user(
            email='prestador-sem-acesso@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )
        outro_prestador = PrestadorEmpresa.objects.create(
            user=outro_user,
            razao_social='Sem Acesso LTDA',
            nome_fantasia='Sem Acesso',
            cnpj='22222222000192',
            endereco='Rua C, 400',
            nome_responsavel='Carlos Lima',
            email='prestador-sem-acesso@example.com',
            telefone='11777777777',
        )
        outro_processo = ProcessoHomologacao.objects.create(prestador=outro_prestador)

        response = self.client.get(reverse('processo-documentos', kwargs={'id_processo': outro_processo.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_validate_document_and_record_audit_fields(self):
        arquivo = SimpleUploadedFile('contrato.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf')
        self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )
        documento = DocumentoPrestador.objects.get()
        admin_user = get_user_model().objects.create_user(
            email='analista@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        token = RefreshToken.for_user(admin_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(
            reverse('admin-documento-validar', kwargs={'id_documento': documento.id}),
            {'status': DocumentoPrestador.Status.APROVADO, 'observacoes': 'Documento conferido.'},
            format='json',
        )

        documento.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(documento.status, DocumentoPrestador.Status.APROVADO)
        self.assertEqual(documento.validado_por, admin_user)
        self.assertIsNotNone(documento.validado_em)
        self.assertEqual(documento.observacoes, 'Documento conferido.')
        self.assertTrue(documento.processo.historico.filter(acao='Documento validado').exists())

    def test_approval_flow_is_created_when_process_enters_internal_approval(self):
        aprovador_1 = get_user_model().objects.create_user(
            email='aprovador-1@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        aprovador_2 = get_user_model().objects.create_user(
            email='aprovador-2@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        processo = ProcessoHomologacao.objects.create(prestador=self.prestador)

        processo.status = ProcessoHomologacao.Status.EM_APROVACAO_INTERNA
        processo.save(update_fields=('status', 'atualizado_em'))

        fluxo = FluxoAprovacao.objects.get(processo=processo)
        etapas = list(fluxo.etapas.order_by('ordem'))

        self.assertEqual(len(etapas), 2)
        self.assertEqual(etapas[0].aprovador, aprovador_1)
        self.assertEqual(etapas[0].ordem, 1)
        self.assertEqual(etapas[0].status, EtapaAprovacao.Status.LIBERADO)
        self.assertIsNotNone(etapas[0].data_liberacao)
        self.assertEqual(etapas[1].aprovador, aprovador_2)
        self.assertEqual(etapas[1].ordem, 2)
        self.assertEqual(etapas[1].status, EtapaAprovacao.Status.AGUARDANDO)
        self.assertTrue(processo.historico.filter(acao='Fluxo de aprovacao criado').exists())

    def test_approval_flow_is_not_duplicated(self):
        get_user_model().objects.create_user(
            email='aprovador-unico@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        processo = ProcessoHomologacao.objects.create(
            prestador=self.prestador,
            status=ProcessoHomologacao.Status.EM_APROVACAO_INTERNA,
        )

        processo.save()

        self.assertEqual(FluxoAprovacao.objects.filter(processo=processo).count(), 1)
        self.assertEqual(EtapaAprovacao.objects.filter(fluxo__processo=processo).count(), 1)

    def test_document_validation_can_generate_approval_flow(self):
        get_user_model().objects.create_user(
            email='aprovador-validacao@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        TipoDocumento.objects.filter(obrigatorio=True).exclude(id=self.tipo_documento.id).update(obrigatorio=False)
        arquivo = SimpleUploadedFile('contrato.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf')
        self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )
        documento = DocumentoPrestador.objects.get()
        admin_user = get_user_model().objects.create_user(
            email='admin-fluxo@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.ADMINISTRADOR,
        )
        token = RefreshToken.for_user(admin_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(
            reverse('admin-documento-validar', kwargs={'id_documento': documento.id}),
            {'status': DocumentoPrestador.Status.APROVADO},
            format='json',
        )

        documento.processo.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(documento.processo.status, ProcessoHomologacao.Status.EM_APROVACAO_INTERNA)
        self.assertTrue(FluxoAprovacao.objects.filter(processo=documento.processo).exists())

    def test_second_approver_cannot_emit_parecer_before_released(self):
        aprovador_1 = get_user_model().objects.create_user(
            email='motor-aprovador-1@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        aprovador_2 = get_user_model().objects.create_user(
            email='motor-aprovador-2@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        processo = ProcessoHomologacao.objects.create(
            prestador=self.prestador,
            status=ProcessoHomologacao.Status.EM_APROVACAO_INTERNA,
        )
        token = RefreshToken.for_user(aprovador_2).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(
            reverse('admin-processo-parecer', kwargs={'id_processo': processo.id}),
            {'decisao': ParecerProcesso.Decisao.APROVADO},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ParecerProcesso.objects.count(), 0)
        self.assertEqual(processo.fluxo_aprovacao.etapas.get(aprovador=aprovador_1).status, EtapaAprovacao.Status.LIBERADO)

    def test_approved_parecer_concludes_current_step_and_releases_next(self):
        aprovador_1 = get_user_model().objects.create_user(
            email='motor-seq-1@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        aprovador_2 = get_user_model().objects.create_user(
            email='motor-seq-2@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        processo = ProcessoHomologacao.objects.create(
            prestador=self.prestador,
            status=ProcessoHomologacao.Status.EM_APROVACAO_INTERNA,
        )
        token = RefreshToken.for_user(aprovador_1).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(
            reverse('admin-processo-parecer', kwargs={'id_processo': processo.id}),
            {'decisao': ParecerProcesso.Decisao.APROVADO, 'observacoes': 'Aprovado pela primeira etapa.'},
            format='json',
        )

        etapa_1 = processo.fluxo_aprovacao.etapas.get(aprovador=aprovador_1)
        etapa_2 = processo.fluxo_aprovacao.etapas.get(aprovador=aprovador_2)
        processo.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(etapa_1.status, EtapaAprovacao.Status.CONCLUIDO)
        self.assertIsNotNone(etapa_1.data_conclusao)
        self.assertEqual(etapa_2.status, EtapaAprovacao.Status.LIBERADO)
        self.assertIsNotNone(etapa_2.data_liberacao)
        self.assertEqual(processo.status, ProcessoHomologacao.Status.EM_APROVACAO_INTERNA)

    def test_last_approved_parecer_approves_process_and_concludes_flow(self):
        aprovador = get_user_model().objects.create_user(
            email='motor-final@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        processo = ProcessoHomologacao.objects.create(
            prestador=self.prestador,
            status=ProcessoHomologacao.Status.EM_APROVACAO_INTERNA,
        )
        token = RefreshToken.for_user(aprovador).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(
            reverse('admin-processo-parecer', kwargs={'id_processo': processo.id}),
            {'decisao': ParecerProcesso.Decisao.APROVADO},
            format='json',
        )

        processo.refresh_from_db()
        fluxo = processo.fluxo_aprovacao
        etapa = fluxo.etapas.get(aprovador=aprovador)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(processo.status, ProcessoHomologacao.Status.APROVADO)
        self.assertEqual(fluxo.status, FluxoAprovacao.Status.CONCLUIDO)
        self.assertIsNotNone(fluxo.encerrado_em)
        self.assertEqual(etapa.status, EtapaAprovacao.Status.CONCLUIDO)
        self.assertTrue(processo.historico.filter(acao='Processo aprovado').exists())

    def test_reproved_parecer_rejects_process_and_closes_flow_atomically(self):
        aprovador = get_user_model().objects.create_user(
            email='motor-reprova@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.EQUIPE_ADMINISTRATIVA,
        )
        processo = ProcessoHomologacao.objects.create(
            prestador=self.prestador,
            status=ProcessoHomologacao.Status.EM_APROVACAO_INTERNA,
        )
        token = RefreshToken.for_user(aprovador).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(
            reverse('admin-processo-parecer', kwargs={'id_processo': processo.id}),
            {'decisao': ParecerProcesso.Decisao.REPROVADO, 'observacoes': 'Risco contratual alto.'},
            format='json',
        )

        processo.refresh_from_db()
        fluxo = processo.fluxo_aprovacao
        etapa = fluxo.etapas.get(aprovador=aprovador)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(processo.status, ProcessoHomologacao.Status.REPROVADO)
        self.assertEqual(fluxo.status, FluxoAprovacao.Status.ENCERRADO)
        self.assertIsNotNone(fluxo.encerrado_em)
        self.assertEqual(etapa.status, EtapaAprovacao.Status.CONCLUIDO)
        self.assertTrue(processo.historico.filter(acao='Processo reprovado', metadados__motivo='Risco contratual alto.').exists())

    def test_prestador_cannot_validate_document(self):
        arquivo = SimpleUploadedFile('contrato.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf')
        self.client.post(
            self.url,
            {'arquivo': arquivo, 'tipo_documento': str(self.tipo_documento.id)},
            format='multipart',
        )
        documento = DocumentoPrestador.objects.get()

        response = self.client.post(
            reverse('admin-documento-validar', kwargs={'id_documento': documento.id}),
            {'status': DocumentoPrestador.Status.APROVADO},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_all_processes(self):
        outro_user = get_user_model().objects.create_user(
            email='outro-prestador@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.PRESTADOR,
        )
        outro_prestador = PrestadorEmpresa.objects.create(
            user=outro_user,
            razao_social='Outra Clinica LTDA',
            nome_fantasia='Outra Clinica',
            cnpj='11111111000191',
            endereco='Rua B, 300',
            nome_responsavel='Ana Souza',
            email='outro-prestador@example.com',
            telefone='11888888888',
        )
        ProcessoHomologacao.objects.create(prestador=self.prestador)
        ProcessoHomologacao.objects.create(prestador=outro_prestador)
        admin_user = get_user_model().objects.create_user(
            email='admin-processos@example.com',
            password='SenhaForte123',
            perfil=get_user_model().Perfil.ADMINISTRADOR,
        )
        token = RefreshToken.for_user(admin_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(reverse('admin-processos'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['processos']), 2)
        self.assertIn('status_atual', response.data['processos'][0])
        self.assertIn('total_documentos', response.data['processos'][0])
        self.assertIn('total_pendencias', response.data['processos'][0])

    def test_prestador_cannot_list_admin_processes(self):
        ProcessoHomologacao.objects.create(prestador=self.prestador)

        response = self.client.get(reverse('admin-processos'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_active_document_types(self):
        TipoDocumento.objects.create(nome='Documento Inativo', ativo=False)

        response = self.client.get(reverse('documentos-tipos'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nomes = {tipo['nome'] for tipo in response.data['tipos_documento']}

        self.assertIn('Contrato Social', nomes)
        self.assertNotIn('Documento Inativo', nomes)
