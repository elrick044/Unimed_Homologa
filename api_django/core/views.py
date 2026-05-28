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

from .models import ConfiguracaoFluxoPadrao, DocumentoPrestador, ParecerProcesso, ProcessoHomologacao, TipoDocumento, User
from .permissions import CanAccessProcess, IsAdministrativeTeam, IsSystemAdmin
from .serializers import (
    ConfiguracaoFluxoPadraoSerializer,
    DocumentoPrestadorHistoricoSerializer,
    DocumentoPrestadorSerializer,
    DocumentoValidacaoSerializer,
    LoginSerializer,
    ParecerProcessoCreateSerializer,
    ParecerProcessoSerializer,
    PrestadorEmpresaSerializer,
    PrestadorRegisterSerializer,
    ProcessoHomologacaoListSerializer,
    ProcessoHomologacaoResumoSerializer,
    TipoDocumentoConfigSerializer,
    TipoDocumentoSerializer,
    UsuarioInternoConfigSerializer,
    UserSessionSerializer,
)
from .services import emitir_parecer_processo


logger = logging.getLogger(__name__)
MAX_EXPECTED_UPLOAD_SIZE = 10 * 1024 * 1024


def log_upload_event(event, **payload):
    logger.info(json.dumps({'event': event, **payload}, ensure_ascii=False))


def log_parecer_event(event, **payload):
    logger.info(json.dumps({'event': event, **payload}, ensure_ascii=False))


def log_config_event(event, **payload):
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
    permission_classes = (IsAuthenticated, CanAccessProcess)

    def get(self, request, id_processo):
        processo = get_object_or_404(ProcessoHomologacao, id=id_processo)
        self.check_object_permissions(request, processo)

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
    permission_classes = (IsAuthenticated, IsAdministrativeTeam)

    def get(self, request):
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


class AdminProcessoDetailView(APIView):
    permission_classes = (IsAuthenticated, IsAdministrativeTeam)

    def get(self, request, id_processo):
        processo = get_object_or_404(
            ProcessoHomologacao.objects.select_related('prestador', 'prestador__user').prefetch_related(
                'documentos',
                'historico',
                'pareceres',
                'fluxo_aprovacao__etapas',
            ),
            id=id_processo,
        )

        return Response(
            ProcessoHomologacaoResumoSerializer(processo).data,
            status=status.HTTP_200_OK,
        )


class AdminDocumentoValidacaoView(APIView):
    permission_classes = (IsAuthenticated, IsAdministrativeTeam)

    def post(self, request, id_documento):
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


class AdminProcessoParecerView(APIView):
    permission_classes = (IsAuthenticated, IsAdministrativeTeam)

    def post(self, request, id_processo):
        processo = get_object_or_404(ProcessoHomologacao, id=id_processo)
        serializer = ParecerProcessoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decisao = serializer.validated_data['decisao']
        observacoes = serializer.validated_data.get('observacoes', '')

        log_parecer_event(
            'parecer_attempt',
            processo_id=processo.id,
            user_id=request.user.id,
            decisao=decisao,
        )

        try:
            context = emitir_parecer_processo(
                processo=processo,
                usuario=request.user,
                decisao=decisao,
                observacoes=observacoes,
                logger=logger,
            )
        except PermissionDenied as exc:
            log_parecer_event(
                'parecer_blocked_order_or_user',
                processo_id=processo.id,
                user_id=request.user.id,
                decisao=decisao,
                detail=str(exc.detail),
            )
            raise
        except ValidationError as exc:
            log_parecer_event(
                'parecer_blocked_state',
                processo_id=processo.id,
                user_id=request.user.id,
                decisao=decisao,
                detail=exc.detail,
            )
            raise

        final_state = context.processo.status in (
            ProcessoHomologacao.Status.APROVADO,
            ProcessoHomologacao.Status.REPROVADO,
        )
        log_parecer_event(
            'parecer_success',
            processo_id=context.processo.id,
            user_id=request.user.id,
            parecer_id=context.parecer.id,
            etapa_id=context.etapa_atual.id,
            decisao=context.decisao,
            processo_status=context.processo.status,
            fluxo_status=context.fluxo.status,
            final_state=final_state,
        )

        if final_state:
            log_parecer_event(
                'parecer_final_state_transition',
                processo_id=context.processo.id,
                parecer_id=context.parecer.id,
                processo_status=context.processo.status,
                fluxo_status=context.fluxo.status,
            )

        return Response(
            {
                'parecer': ParecerProcessoSerializer(context.parecer).data,
                'processo_status': context.processo.status,
                'fluxo_status': context.fluxo.status,
                'etapa_status': context.etapa_atual.status,
                'proxima_etapa': context.proxima_etapa.id if context.proxima_etapa else None,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminConfigUsuarioListCreateView(APIView):
    permission_classes = (IsAuthenticated, IsSystemAdmin)

    def get(self, request):
        usuarios = User.objects.filter(
            perfil__in=(User.Perfil.EQUIPE_ADMINISTRATIVA, User.Perfil.ADMINISTRADOR),
        ).order_by('email')
        return Response(
            {'usuarios': UsuarioInternoConfigSerializer(usuarios, many=True).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = UsuarioInternoConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        log_config_event(
            'config_user_created',
            actor_id=request.user.id,
            user_id=usuario.id,
            new_state=UsuarioInternoConfigSerializer(usuario).data,
        )
        return Response(UsuarioInternoConfigSerializer(usuario).data, status=status.HTTP_201_CREATED)


class AdminConfigUsuarioDetailView(APIView):
    permission_classes = (IsAuthenticated, IsSystemAdmin)

    def get_object(self, id_usuario):
        return get_object_or_404(
            User,
            id=id_usuario,
            perfil__in=(User.Perfil.EQUIPE_ADMINISTRATIVA, User.Perfil.ADMINISTRADOR),
        )

    def get(self, request, id_usuario):
        usuario = self.get_object(id_usuario)
        return Response(UsuarioInternoConfigSerializer(usuario).data, status=status.HTTP_200_OK)

    def put(self, request, id_usuario):
        usuario = self.get_object(id_usuario)
        previous_state = UsuarioInternoConfigSerializer(usuario).data
        serializer = UsuarioInternoConfigSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        new_state = UsuarioInternoConfigSerializer(usuario).data
        log_config_event(
            'config_user_updated',
            actor_id=request.user.id,
            user_id=usuario.id,
            previous_state=previous_state,
            new_state=new_state,
        )
        return Response(new_state, status=status.HTTP_200_OK)

    def delete(self, request, id_usuario):
        usuario = self.get_object(id_usuario)
        previous_state = UsuarioInternoConfigSerializer(usuario).data
        usuario.is_active = False
        usuario.save(update_fields=('is_active',))
        new_state = UsuarioInternoConfigSerializer(usuario).data
        log_config_event(
            'config_user_deactivated',
            actor_id=request.user.id,
            user_id=usuario.id,
            previous_state=previous_state,
            new_state=new_state,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminConfigDocumentoListCreateView(APIView):
    permission_classes = (IsAuthenticated, IsSystemAdmin)

    def get(self, request):
        documentos = TipoDocumento.objects.all().order_by('nome')
        return Response(
            {'documentos': TipoDocumentoConfigSerializer(documentos, many=True).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = TipoDocumentoConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        documento = serializer.save()
        log_config_event(
            'config_document_type_created',
            actor_id=request.user.id,
            document_type_id=documento.id,
            new_state=TipoDocumentoConfigSerializer(documento).data,
        )
        return Response(TipoDocumentoConfigSerializer(documento).data, status=status.HTTP_201_CREATED)


class AdminConfigDocumentoDetailView(APIView):
    permission_classes = (IsAuthenticated, IsSystemAdmin)

    def get_object(self, id_tipo_documento):
        return get_object_or_404(TipoDocumento, id=id_tipo_documento)

    def get(self, request, id_tipo_documento):
        documento = self.get_object(id_tipo_documento)
        return Response(TipoDocumentoConfigSerializer(documento).data, status=status.HTTP_200_OK)

    def put(self, request, id_tipo_documento):
        documento = self.get_object(id_tipo_documento)
        previous_state = TipoDocumentoConfigSerializer(documento).data
        serializer = TipoDocumentoConfigSerializer(documento, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        documento = serializer.save()
        new_state = TipoDocumentoConfigSerializer(documento).data
        log_config_event(
            'config_document_type_updated',
            actor_id=request.user.id,
            document_type_id=documento.id,
            previous_state=previous_state,
            new_state=new_state,
        )
        return Response(new_state, status=status.HTTP_200_OK)

    def delete(self, request, id_tipo_documento):
        documento = self.get_object(id_tipo_documento)
        previous_state = TipoDocumentoConfigSerializer(documento).data
        documento.ativo = False
        documento.save(update_fields=('ativo', 'atualizado_em'))
        new_state = TipoDocumentoConfigSerializer(documento).data
        log_config_event(
            'config_document_type_deactivated',
            actor_id=request.user.id,
            document_type_id=documento.id,
            previous_state=previous_state,
            new_state=new_state,
            critical=bool(previous_state.get('obrigatorio')),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminConfigFluxoListCreateView(APIView):
    permission_classes = (IsAuthenticated, IsSystemAdmin)

    def get(self, request):
        fluxos = ConfiguracaoFluxoPadrao.objects.prefetch_related('etapas__aprovador').order_by('nome')
        return Response(
            {'fluxos': ConfiguracaoFluxoPadraoSerializer(fluxos, many=True).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = ConfiguracaoFluxoPadraoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fluxo = serializer.save()
        log_config_event(
            'config_approval_flow_created',
            actor_id=request.user.id,
            flow_config_id=fluxo.id,
            new_state=ConfiguracaoFluxoPadraoSerializer(fluxo).data,
        )
        return Response(ConfiguracaoFluxoPadraoSerializer(fluxo).data, status=status.HTTP_201_CREATED)


class AdminConfigFluxoDetailView(APIView):
    permission_classes = (IsAuthenticated, IsSystemAdmin)

    def get_object(self, id_fluxo):
        return get_object_or_404(ConfiguracaoFluxoPadrao, id=id_fluxo)

    def get(self, request, id_fluxo):
        fluxo = self.get_object(id_fluxo)
        return Response(ConfiguracaoFluxoPadraoSerializer(fluxo).data, status=status.HTTP_200_OK)

    def put(self, request, id_fluxo):
        fluxo = self.get_object(id_fluxo)
        previous_state = ConfiguracaoFluxoPadraoSerializer(fluxo).data
        serializer = ConfiguracaoFluxoPadraoSerializer(fluxo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        fluxo = serializer.save()
        new_state = ConfiguracaoFluxoPadraoSerializer(fluxo).data
        log_config_event(
            'config_approval_flow_updated',
            actor_id=request.user.id,
            flow_config_id=fluxo.id,
            previous_state=previous_state,
            new_state=new_state,
        )
        return Response(new_state, status=status.HTTP_200_OK)

    def delete(self, request, id_fluxo):
        fluxo = self.get_object(id_fluxo)
        previous_state = ConfiguracaoFluxoPadraoSerializer(fluxo).data
        fluxo.ativo = False
        fluxo.save(update_fields=('ativo', 'atualizado_em'))
        new_state = ConfiguracaoFluxoPadraoSerializer(fluxo).data
        log_config_event(
            'config_approval_flow_deactivated',
            actor_id=request.user.id,
            flow_config_id=fluxo.id,
            previous_state=previous_state,
            new_state=new_state,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
