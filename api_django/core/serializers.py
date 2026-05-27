import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import (
    DocumentoPrestador,
    EtapaAprovacao,
    FluxoAprovacao,
    HistoricoProcesso,
    ParecerProcesso,
    PrestadorEmpresa,
    ProcessoHomologacao,
    TipoDocumento,
    User,
)


CNPJ_FORMAT_RE = re.compile(r'^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$')


def normalize_cnpj(value):
    return re.sub(r'\D', '', value or '')


def validate_cnpj_format(value):
    if not CNPJ_FORMAT_RE.match(value or ''):
        raise serializers.ValidationError('CNPJ deve estar no formato 00.000.000/0000-00 ou conter 14 digitos.')

    digits = normalize_cnpj(value)
    if len(digits) != 14:
        raise serializers.ValidationError('CNPJ deve conter 14 digitos.')

    return digits


class PrestadorRegisterSerializer(serializers.Serializer):
    razao_social = serializers.CharField(max_length=255)
    nome_fantasia = serializers.CharField(max_length=255)
    cnpj = serializers.CharField(max_length=18)
    endereco = serializers.CharField()
    nome_responsavel = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    telefone = serializers.CharField(max_length=20)
    senha = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    def validate_cnpj(self, value):
        cnpj = validate_cnpj_format(value)

        if PrestadorEmpresa.objects.filter(cnpj=cnpj).exists():
            raise serializers.ValidationError('Ja existe um prestador cadastrado com este CNPJ.')

        return cnpj

    def validate_email(self, value):
        email = value.lower()

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Ja existe um usuario cadastrado com este e-mail.')

        return email

    def validate_senha(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('senha')
        email = validated_data['email']

        user = User.objects.create_user(
            email=email,
            password=password,
            perfil=User.Perfil.PRESTADOR,
        )
        prestador = PrestadorEmpresa.objects.create(user=user, **validated_data)
        processo = ProcessoHomologacao.objects.create(prestador=prestador)
        processo.registrar_evento(
            acao='Cadastro criado',
            descricao='Cadastro do prestador criado e processo de homologacao iniciado.',
            usuario=user,
        )
        return prestador


class PrestadorEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrestadorEmpresa
        fields = (
            'id',
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'endereco',
            'nome_responsavel',
            'email',
            'telefone',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = ('id', 'criado_em', 'atualizado_em')


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('senha')
        request = self.context.get('request')
        user = authenticate(request=request, username=email, password=password)

        if not user:
            raise serializers.ValidationError('E-mail ou senha invalidos.')

        if not user.is_active:
            raise serializers.ValidationError('Usuario inativo.')

        attrs['user'] = user
        return attrs


class UserSessionSerializer(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'perfil', 'nome')

    def get_nome(self, obj):
        full_name = obj.get_full_name()
        if full_name:
            return full_name

        prestador = getattr(obj, 'prestador_empresa', None)
        if prestador:
            return prestador.nome_responsavel or prestador.razao_social

        return obj.email


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ('id', 'nome', 'descricao', 'obrigatorio', 'ativo', 'criado_em', 'atualizado_em')
        read_only_fields = ('id', 'criado_em', 'atualizado_em')


class DocumentoPrestadorSerializer(serializers.ModelSerializer):
    tipo_documento = TipoDocumentoSerializer(read_only=True)
    arquivo = serializers.FileField(read_only=True)
    documento_anterior = serializers.PrimaryKeyRelatedField(read_only=True)
    validado_por_email = serializers.EmailField(source='validado_por.email', read_only=True)

    class Meta:
        model = DocumentoPrestador
        fields = (
            'id',
            'tipo_documento',
            'arquivo',
            'content_type',
            'tamanho_bytes',
            'status',
            'versao',
            'documento_anterior',
            'validado_por_email',
            'validado_em',
            'motivo_reprovacao',
            'observacoes',
            'enviado_em',
        )
        read_only_fields = fields


class DocumentoPrestadorVersaoSerializer(DocumentoPrestadorSerializer):
    class Meta(DocumentoPrestadorSerializer.Meta):
        fields = DocumentoPrestadorSerializer.Meta.fields


class DocumentoPrestadorHistoricoSerializer(serializers.Serializer):
    tipo_documento = TipoDocumentoSerializer(read_only=True)
    documento_atual = DocumentoPrestadorVersaoSerializer(read_only=True)
    versoes = DocumentoPrestadorVersaoSerializer(many=True, read_only=True)


class DocumentoValidacaoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        DocumentoPrestador.Status.APROVADO,
        DocumentoPrestador.Status.REPROVADO,
    ))
    motivo_reprovacao = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    observacoes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if attrs['status'] == DocumentoPrestador.Status.REPROVADO and not attrs.get('motivo_reprovacao'):
            raise serializers.ValidationError({'motivo_reprovacao': ['Informe o motivo da reprovacao.']})

        return attrs


class HistoricoProcessoSerializer(serializers.ModelSerializer):
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)

    class Meta:
        model = HistoricoProcesso
        fields = ('id', 'acao', 'descricao', 'usuario_email', 'metadados', 'criado_em')
        read_only_fields = fields


class EtapaAprovacaoSerializer(serializers.ModelSerializer):
    aprovador_email = serializers.EmailField(source='aprovador.email', read_only=True)
    aprovador_nome = serializers.SerializerMethodField()

    class Meta:
        model = EtapaAprovacao
        fields = (
            'id',
            'aprovador',
            'aprovador_email',
            'aprovador_nome',
            'ordem',
            'status',
            'data_liberacao',
            'data_conclusao',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = fields

    def get_aprovador_nome(self, obj):
        return obj.aprovador.get_full_name() or obj.aprovador.email


class FluxoAprovacaoSerializer(serializers.ModelSerializer):
    etapas = EtapaAprovacaoSerializer(many=True, read_only=True)

    class Meta:
        model = FluxoAprovacao
        fields = ('id', 'status', 'iniciado_em', 'encerrado_em', 'atualizado_em', 'etapas')
        read_only_fields = fields


class ParecerProcessoSerializer(serializers.ModelSerializer):
    aprovador_email = serializers.EmailField(source='aprovador.email', read_only=True)

    class Meta:
        model = ParecerProcesso
        fields = (
            'id',
            'aprovador',
            'aprovador_email',
            'etapa',
            'decisao',
            'observacoes',
            'data_hora',
            'docusign_envelope_id',
            'docusign_recipient_id',
            'docusign_status',
            'docusign_assinado_em',
        )
        read_only_fields = fields


class ParecerProcessoCreateSerializer(serializers.Serializer):
    decisao = serializers.ChoiceField(choices=ParecerProcesso.Decisao.choices)
    observacoes = serializers.CharField(required=False, allow_blank=True)


class ProcessoHomologacaoResumoSerializer(serializers.ModelSerializer):
    prestador = PrestadorEmpresaSerializer(read_only=True)
    status_atual = serializers.CharField(source='status', read_only=True)
    pendencias = serializers.SerializerMethodField()
    documentos_enviados = serializers.SerializerMethodField()
    historico = HistoricoProcessoSerializer(many=True, read_only=True)
    fluxo_aprovacao = FluxoAprovacaoSerializer(read_only=True)
    pareceres = ParecerProcessoSerializer(many=True, read_only=True)

    class Meta:
        model = ProcessoHomologacao
        fields = (
            'id',
            'prestador',
            'status_atual',
            'criado_em',
            'atualizado_em',
            'concluido_em',
            'pendencias',
            'documentos_enviados',
            'historico',
            'fluxo_aprovacao',
            'pareceres',
        )
        read_only_fields = fields

    def get_pendencias(self, obj):
        documentos_enviados = obj.documentos.exclude(
            status__in=(DocumentoPrestador.Status.REPROVADO, DocumentoPrestador.Status.SUBSTITUIDO)
        ).values_list('tipo_documento_id', flat=True).distinct()
        pendencias = TipoDocumento.objects.filter(ativo=True, obrigatorio=True).exclude(id__in=documentos_enviados)
        return TipoDocumentoSerializer(pendencias, many=True).data

    def get_documentos_enviados(self, obj):
        documentos = obj.documentos.exclude(
            status=DocumentoPrestador.Status.SUBSTITUIDO
        ).select_related('tipo_documento').order_by('-enviado_em')
        return DocumentoPrestadorSerializer(documentos, many=True).data


class ProcessoHomologacaoListSerializer(serializers.ModelSerializer):
    prestador = PrestadorEmpresaSerializer(read_only=True)
    status_atual = serializers.CharField(source='status', read_only=True)
    total_documentos = serializers.SerializerMethodField()
    total_pendencias = serializers.SerializerMethodField()
    ultimo_evento = serializers.SerializerMethodField()

    class Meta:
        model = ProcessoHomologacao
        fields = (
            'id',
            'prestador',
            'status_atual',
            'total_documentos',
            'total_pendencias',
            'ultimo_evento',
            'criado_em',
            'atualizado_em',
            'concluido_em',
        )
        read_only_fields = fields

    def get_total_documentos(self, obj):
        return obj.documentos.exclude(status=DocumentoPrestador.Status.SUBSTITUIDO).count()

    def get_total_pendencias(self, obj):
        documentos_enviados = obj.documentos.exclude(
            status__in=(DocumentoPrestador.Status.REPROVADO, DocumentoPrestador.Status.SUBSTITUIDO)
        ).values_list('tipo_documento_id', flat=True).distinct()
        return TipoDocumento.objects.filter(ativo=True, obrigatorio=True).exclude(id__in=documentos_enviados).count()

    def get_ultimo_evento(self, obj):
        evento = obj.historico.order_by('-criado_em').first()
        if not evento:
            return None

        return HistoricoProcessoSerializer(evento).data
