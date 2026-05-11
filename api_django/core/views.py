import json
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DocumentoPrestador, TipoDocumento, User
from .serializers import (
    DocumentoPrestadorSerializer,
    LoginSerializer,
    PrestadorEmpresaSerializer,
    PrestadorRegisterSerializer,
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
                documento = DocumentoPrestador.objects.create(
                    prestador=prestador,
                    tipo_documento=item['tipo_documento'],
                    arquivo=item['arquivo'],
                    content_type=item['content_type'],
                    tamanho_bytes=item['tamanho_bytes'],
                )
                documentos.append(documento)

                log_upload_event(
                    'document_upload_success',
                    user_id=user.id,
                    prestador_id=prestador.id,
                    documento_id=documento.id,
                    tipo_documento_id=item['tipo_documento'].id,
                    filename=item['arquivo'].name,
                    size=item['tamanho_bytes'],
                )

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
