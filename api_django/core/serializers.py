import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import (
    ConfiguracaoFluxoPadrao,
    DocumentoPrestador,
    EtapaConfiguracaoPadrao,
    EtapaAprovacao,
    FluxoAprovacao,
    HistoricoProcesso,
    MinutaContrato,
    ParecerProcesso,
    PrestadorEmpresa,
    ProcessoHomologacao,
    TemplateContrato,
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


class UsuarioInternoConfigSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8, style={'input_type': 'password'})
    nome = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'perfil',
            'first_name',
            'last_name',
            'nome',
            'is_active',
            'password',
            'date_joined',
            'last_login',
        )
        read_only_fields = ('id', 'nome', 'date_joined', 'last_login')

    def get_nome(self, obj):
        return obj.get_full_name() or obj.email

    def validate_perfil(self, value):
        if value not in (User.Perfil.EQUIPE_ADMINISTRATIVA, User.Perfil.ADMINISTRADOR):
            raise serializers.ValidationError('Apenas usuarios internos podem ser gerenciados por esta rota.')

        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': ['Informe uma senha inicial.']})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ('id', 'nome', 'descricao', 'obrigatorio', 'ativo', 'criado_em', 'atualizado_em')
        read_only_fields = ('id', 'criado_em', 'atualizado_em')


class TipoDocumentoConfigSerializer(serializers.ModelSerializer):
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


class EtapaConfiguracaoPadraoSerializer(serializers.ModelSerializer):
    aprovador_email = serializers.EmailField(source='aprovador.email', read_only=True)
    aprovador_nome = serializers.SerializerMethodField()

    class Meta:
        model = EtapaConfiguracaoPadrao
        fields = ('id', 'aprovador', 'aprovador_email', 'aprovador_nome', 'ordem')
        read_only_fields = ('id', 'aprovador_email', 'aprovador_nome')

    def get_aprovador_nome(self, obj):
        return obj.aprovador.get_full_name() or obj.aprovador.email

    def validate_aprovador(self, value):
        if value.perfil != User.Perfil.EQUIPE_ADMINISTRATIVA or not value.is_active:
            raise serializers.ValidationError('O aprovador deve ser um usuario ativo da equipe administrativa.')

        return value


class ConfiguracaoFluxoPadraoSerializer(serializers.ModelSerializer):
    etapas = EtapaConfiguracaoPadraoSerializer(many=True)

    class Meta:
        model = ConfiguracaoFluxoPadrao
        fields = ('id', 'nome', 'ativo', 'etapas', 'criado_em', 'atualizado_em')
        read_only_fields = ('id', 'criado_em', 'atualizado_em')

    def validate_etapas(self, etapas):
        if not etapas:
            raise serializers.ValidationError('Informe ao menos uma etapa de aprovacao.')

        ordens = [etapa['ordem'] for etapa in etapas]
        if len(ordens) != len(set(ordens)):
            raise serializers.ValidationError('A ordem das etapas nao pode se repetir.')

        aprovadores = [etapa['aprovador'].id for etapa in etapas]
        if len(aprovadores) != len(set(aprovadores)):
            raise serializers.ValidationError('Um aprovador nao pode se repetir na mesma configuracao.')

        return etapas

    @transaction.atomic
    def create(self, validated_data):
        etapas_data = validated_data.pop('etapas')
        configuracao = ConfiguracaoFluxoPadrao.objects.create(**validated_data)
        self._replace_etapas(configuracao, etapas_data)
        self._ensure_single_active(configuracao)
        return configuracao

    @transaction.atomic
    def update(self, instance, validated_data):
        etapas_data = validated_data.pop('etapas', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if etapas_data is not None:
            self._replace_etapas(instance, etapas_data)

        self._ensure_single_active(instance)
        return instance

    def _replace_etapas(self, configuracao, etapas_data):
        configuracao.etapas.all().delete()
        for etapa_data in sorted(etapas_data, key=lambda item: item['ordem']):
            EtapaConfiguracaoPadrao.objects.create(configuracao=configuracao, **etapa_data)

    def _ensure_single_active(self, configuracao):
        if configuracao.ativo:
            ConfiguracaoFluxoPadrao.objects.exclude(id=configuracao.id).update(ativo=False)


class TemplateContratoSerializer(serializers.ModelSerializer):
    template_anterior = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TemplateContrato
        fields = (
            'id',
            'nome',
            'conteudo_html',
            'ativo',
            'versao',
            'template_anterior',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = ('id', 'versao', 'template_anterior', 'criado_em', 'atualizado_em')

    @transaction.atomic
    def create(self, validated_data):
        template = TemplateContrato.objects.create(**validated_data)
        self._ensure_single_active(template)
        return template

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.ativo:
            novo_template = TemplateContrato.objects.create(
                nome=validated_data.get('nome', instance.nome),
                conteudo_html=validated_data.get('conteudo_html', instance.conteudo_html),
                ativo=validated_data.get('ativo', True),
                versao=instance.versao + 1,
                template_anterior=instance,
            )
            instance.ativo = False
            instance.save(update_fields=('ativo', 'atualizado_em'))
            self._ensure_single_active(novo_template)
            return novo_template

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self._ensure_single_active(instance)
        return instance

    def _ensure_single_active(self, template):
        if template.ativo:
            TemplateContrato.objects.exclude(id=template.id).update(ativo=False)


class MinutaContratoSerializer(serializers.ModelSerializer):
    template_id = serializers.IntegerField(source='template.id', read_only=True)
    template_nome = serializers.CharField(source='template.nome', read_only=True)
    template_versao = serializers.IntegerField(source='template.versao', read_only=True)
    arquivo_pdf = serializers.FileField(read_only=True)

    class Meta:
        model = MinutaContrato
        fields = ('id', 'template_id', 'template_nome', 'template_versao', 'arquivo_pdf', 'gerado_em')
        read_only_fields = fields


class ProcessoHomologacaoResumoSerializer(serializers.ModelSerializer):
    prestador = PrestadorEmpresaSerializer(read_only=True)
    status_atual = serializers.CharField(source='status', read_only=True)
    pendencias = serializers.SerializerMethodField()
    documentos_enviados = serializers.SerializerMethodField()
    historico = HistoricoProcessoSerializer(many=True, read_only=True)
    fluxo_aprovacao = FluxoAprovacaoSerializer(read_only=True)
    pareceres = ParecerProcessoSerializer(many=True, read_only=True)
    minuta_contrato = MinutaContratoSerializer(read_only=True)

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
            'minuta_contrato',
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
