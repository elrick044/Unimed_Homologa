import json
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DocumentoPrestador, ProcessoHomologacao, TipoDocumento, User
from .serializers import (
    DocumentoPrestadorHistoricoSerializer,
    DocumentoPrestadorSerializer,
    DocumentoValidacaoSerializer,
    LoginSerializer,
    PrestadorEmpresaSerializer,
    PrestadorRegisterSerializer,
    ProcessoHomologacaoListSerializer,
    ProcessoHomologacaoResumoSerializer,
    TipoDocumentoSerializer,
    UserSessionSerializer,
)


logger = logging.getLogger(__name__)
MAX_EXPECTED_UPLOAD_SIZE = 10 * 1024 * 1024


def log_upload_event(event, **payload):
    logger.info(json.dumps({'event': event, **payload}, ensure_ascii=False))


def is_pdf_file(uploaded_file):
    if getattr(uploaded_file, 'content_type', '') != 'application/pdf':
        return False

    if not uploaded_file.name.lower().endswith('.pdf'):
        return False

    position = uploaded_file.tell()
    header = uploaded_file.read(4)
    uploaded_file.seek(position)
    return header == b'%PDF'


def get_or_create_processo(prestador, usuario=None):
    processo, created = ProcessoHomologacao.objects.get_or_create(prestador=prestador)

    if created:
        processo.registrar_evento(
            acao='Cadastro criado',
            descricao='Processo de homologacao criado automaticamente.',
            usuario=usuario,
        )

    return processo


def is_admin_profile(user):
    return user.perfil in (User.Perfil.EQUIPE_ADMINISTRATIVA, User.Perfil.ADMINISTRADOR)


class PrestadorRegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PrestadorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prestador = serializer.save()

        return Response(
            PrestadorEmpresaSerializer(prestador).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSessionSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(
            UserSessionSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


class DocumentoUploadView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        user = request.user

        if user.perfil != User.Perfil.PRESTADOR:
            log_upload_event('document_upload_forbidden_profile', user_id=user.id, perfil=user.perfil)
            raise PermissionDenied('Apenas prestadores podem enviar documentos.')

        prestador = getattr(user, 'prestador_empresa', None)
        if not prestador:
            log_upload_event('document_upload_missing_prestador', user_id=user.id)
            raise PermissionDenied('Usuario nao possui perfil de prestador vinculado.')

        processo = get_or_create_processo(prestador, usuario=user)
        arquivos = request.FILES.getlist('arquivos') or request.FILES.getlist('arquivo')
        tipos_documento = request.data.getlist('tipos_documento') or request.data.getlist('tipo_documento')

        if not arquivos:
            log_upload_event('document_upload_validation_failed', user_id=user.id, reason='missing_files')
            raise ValidationError({'arquivos': ['Envie ao menos um arquivo PDF.']})

        if len(arquivos) != len(tipos_documento):
            log_upload_event(
                'document_upload_validation_failed',
                user_id=user.id,
                reason='files_and_types_length_mismatch',
                files_count=len(arquivos),
                types_count=len(tipos_documento),
            )
            raise ValidationError({'tipos_documento': ['Informe um tipo de documento para cada arquivo enviado.']})

        documentos_para_criar = []

        for arquivo, tipo_documento_id in zip(arquivos, tipos_documento):
            content_type = getattr(arquivo, 'content_type', '')
            tamanho_bytes = getattr(arquivo, 'size', 0)

            if tamanho_bytes > MAX_EXPECTED_UPLOAD_SIZE:
                log_upload_event(
                    'document_upload_size_anomaly',
                    user_id=user.id,
                    filename=arquivo.name,
                    size=tamanho_bytes,
                    max_expected_size=MAX_EXPECTED_UPLOAD_SIZE,
                )

            if not is_pdf_file(arquivo):
                log_upload_event(
                    'document_upload_invalid_format',
                    user_id=user.id,
                    filename=arquivo.name,
                    content_type=content_type,
                )
                raise ValidationError({'arquivos': [f'O arquivo {arquivo.name} deve ser um PDF.']})

            try:
                tipo_documento = TipoDocumento.objects.get(id=tipo_documento_id, ativo=True)
            except (TipoDocumento.DoesNotExist, ValueError):
                log_upload_event(
                    'document_upload_validation_failed',
                    user_id=user.id,
                    reason='invalid_tipo_documento',
                    tipo_documento_id=tipo_documento_id,
                )
                raise ValidationError({'tipos_documento': ['Tipo de documento invalido ou inativo.']})

            documentos_para_criar.append(
                {
                    'arquivo': arquivo,
                    'tipo_documento': tipo_documento,
                    'content_type': content_type,
                    'tamanho_bytes': tamanho_bytes,
                }
            )

        documentos = []

        with transaction.atomic():
            for item in documentos_para_criar:
                documento_anterior = processo.documentos.filter(
                    tipo_documento=item['tipo_documento'],
                ).exclude(status=DocumentoPrestador.Status.SUBSTITUIDO).order_by('-versao', '-enviado_em').first()
                versao = 1

                if documento_anterior:
                    versao = documento_anterior.versao + 1
                    documento_anterior.status = DocumentoPrestador.Status.SUBSTITUIDO
                    documento_anterior.save(update_fields=('status',))
                    processo.registrar_evento(
                        acao='Documento substituido',
                        descricao=f'Documento {item["tipo_documento"].nome} substituido por nova versao.',
                        usuario=user,
                        metadados={
                            'documento_substituido_id': documento_anterior.id,
                            'versao_substituida': documento_anterior.versao,
                        },
                    )

                documento = DocumentoPrestador.objects.create(
                    prestador=prestador,
                    processo=processo,
                    tipo_documento=item['tipo_documento'],
                    arquivo=item['arquivo'],
                    content_type=item['content_type'],
                    tamanho_bytes=item['tamanho_bytes'],
                    versao=versao,
                    documento_anterior=documento_anterior,
                )
                documentos.append(documento)
                processo.registrar_evento(
                    acao='Documento enviado',
                    descricao=f'Documento {item["tipo_documento"].nome} enviado pelo prestador.',
                    usuario=user,
                    metadados={
                        'documento_id': documento.id,
                        'tipo_documento_id': item['tipo_documento'].id,
                        'arquivo_nome': item['arquivo'].name,
                        'tamanho_bytes': item['tamanho_bytes'],
                        'versao': documento.versao,
                        'documento_anterior_id': documento_anterior.id if documento_anterior else None,
                    },
                )

                log_upload_event(
                    'document_upload_success',
                    user_id=user.id,
                    prestador_id=prestador.id,
                    documento_id=documento.id,
                    tipo_documento_id=item['tipo_documento'].id,
                    filename=item['arquivo'].name,
                    size=item['tamanho_bytes'],
                )

            processo.atualizar_status_por_documentos(usuario=user)

        return Response(
            {'documentos': DocumentoPrestadorSerializer(documentos, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class TipoDocumentoListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tipos_documento = TipoDocumento.objects.filter(ativo=True).order_by('nome')
        return Response(
            {'tipos_documento': TipoDocumentoSerializer(tipos_documento, many=True).data},
            status=status.HTTP_200_OK,
        )


class PrestadorProcessoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user

        if user.perfil != User.Perfil.PRESTADOR:
            raise PermissionDenied('Apenas prestadores podem consultar este processo.')

        prestador = getattr(user, 'prestador_empresa', None)
        if not prestador:
            raise PermissionDenied('Usuario nao possui perfil de prestador vinculado.')

        processo = get_or_create_processo(prestador, usuario=user)
        return Response(
            ProcessoHomologacaoResumoSerializer(processo).data,
            status=status.HTTP_200_OK,
        )


class ProcessoDocumentoListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, id_processo):
        processo = get_object_or_404(ProcessoHomologacao, id=id_processo)

        if not is_admin_profile(request.user):
            prestador = getattr(request.user, 'prestador_empresa', None)
            if not prestador or processo.prestador_id != prestador.id:
                raise PermissionDenied('Usuario nao possui acesso a este processo.')

        grupos = []
        tipos_documento = TipoDocumento.objects.filter(
            documentos_prestadores__processo=processo,
        ).distinct().order_by('nome')

        for tipo_documento in tipos_documento:
            versoes = processo.documentos.filter(
                tipo_documento=tipo_documento,
            ).select_related('tipo_documento', 'validado_por').order_by('-versao', '-enviado_em')
            documento_atual = versoes.exclude(status=DocumentoPrestador.Status.SUBSTITUIDO).first()
            grupos.append({
                'tipo_documento': tipo_documento,
                'documento_atual': documento_atual,
                'versoes': list(versoes),
            })

        return Response(
            {'processo': processo.id, 'documentos': DocumentoPrestadorHistoricoSerializer(grupos, many=True).data},
            status=status.HTTP_200_OK,
        )


class AdminProcessoListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not is_admin_profile(request.user):
            raise PermissionDenied('Apenas perfis administrativos podem listar processos.')

        processos = ProcessoHomologacao.objects.select_related(
            'prestador',
            'prestador__user',
        ).prefetch_related(
            'documentos',
            'historico',
        ).order_by('-criado_em')

        return Response(
            {'processos': ProcessoHomologacaoListSerializer(processos, many=True).data},
            status=status.HTTP_200_OK,
        )


class AdminDocumentoValidacaoView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, id_documento):
        if not is_admin_profile(request.user):
            raise PermissionDenied('Apenas perfis administrativos podem validar documentos.')

        documento = get_object_or_404(DocumentoPrestador, id=id_documento)
        serializer = DocumentoValidacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        novo_status = validated_data['status']

        with transaction.atomic():
            documento.status = novo_status
            documento.validado_por = request.user
            documento.validado_em = timezone.now()
            documento.motivo_reprovacao = validated_data.get('motivo_reprovacao') if novo_status == DocumentoPrestador.Status.REPROVADO else None
            documento.observacoes = validated_data.get('observacoes')
            documento.save(update_fields=(
                'status',
                'validado_por',
                'validado_em',
                'motivo_reprovacao',
                'observacoes',
            ))

            processo = documento.processo
            processo.registrar_evento(
                acao='Documento validado',
                descricao=f'Documento {documento.tipo_documento.nome} marcado como {novo_status}.',
                usuario=request.user,
                metadados={
                    'documento_id': documento.id,
                    'tipo_documento_id': documento.tipo_documento_id,
                    'status': novo_status,
                    'motivo_reprovacao': documento.motivo_reprovacao,
                    'observacoes': documento.observacoes,
                    'versao': documento.versao,
                },
            )

            status_anterior = processo.status
            if novo_status == DocumentoPrestador.Status.REPROVADO:
                processo.status = ProcessoHomologacao.Status.CORRECAO_SOLICITADA
            else:
                tipos_aprovados = processo.documentos.filter(
                    status=DocumentoPrestador.Status.APROVADO,
                    tipo_documento__ativo=True,
                    tipo_documento__obrigatorio=True,
                ).values_list('tipo_documento_id', flat=True).distinct()
                possui_pendencias_de_aprovacao = TipoDocumento.objects.filter(
                    ativo=True,
                    obrigatorio=True,
                ).exclude(id__in=tipos_aprovados).exists()

                if not possui_pendencias_de_aprovacao:
                    processo.status = ProcessoHomologacao.Status.EM_APROVACAO_INTERNA

            if processo.status != status_anterior:
                processo.save(update_fields=('status', 'atualizado_em'))
                processo.registrar_evento(
                    acao='Status atualizado',
                    descricao=f'Status alterado de {status_anterior} para {processo.status}.',
                    usuario=request.user,
                    metadados={'status_anterior': status_anterior, 'status_atual': processo.status},
                )

        return Response(
            DocumentoPrestadorSerializer(documento).data,
            status=status.HTTP_200_OK,
        )
