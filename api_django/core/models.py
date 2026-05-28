from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('O e-mail e obrigatorio.')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('perfil', User.Perfil.ADMINISTRADOR)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario deve ter is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Perfil(models.TextChoices):
        PRESTADOR = 'PRESTADOR', _('Prestador de Servico')
        EQUIPE_ADMINISTRATIVA = 'EQUIPE_ADMINISTRATIVA', _('Equipe Administrativa')
        ADMINISTRADOR = 'ADMINISTRADOR', _('Administrador do Sistema')

    username = None
    email = models.EmailField(unique=True)
    perfil = models.CharField(
        max_length=30,
        choices=Perfil.choices,
        default=Perfil.PRESTADOR,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class PrestadorEmpresa(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='prestador_empresa',
    )
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, unique=True)
    endereco = models.TextField()
    nome_responsavel = models.CharField(max_length=255)
    email = models.EmailField()
    telefone = models.CharField(max_length=20)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prestador Empresa'
        verbose_name_plural = 'Prestadores Empresa'

    def __str__(self):
        return f'{self.razao_social} ({self.cnpj})'


class TipoDocumento(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    descricao = models.TextField(blank=True)
    obrigatorio = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documento'
        ordering = ('nome',)

    def __str__(self):
        return self.nome


class ProcessoHomologacao(models.Model):
    class Status(models.TextChoices):
        CADASTRO_INICIADO = 'CADASTRO_INICIADO', _('Cadastro iniciado')
        DOCUMENTACAO_PENDENTE = 'DOCUMENTACAO_PENDENTE', _('Documentacao pendente')
        EM_VALIDACAO = 'EM_VALIDACAO', _('Em validacao')
        CORRECAO_SOLICITADA = 'CORRECAO_SOLICITADA', _('Correcao solicitada')
        EM_APROVACAO_INTERNA = 'EM_APROVACAO_INTERNA', _('Em aprovacao interna')
        REPROVADO = 'REPROVADO', _('Reprovado')
        APROVADO = 'APROVADO', _('Aprovado')
        MINUTA_GERADA = 'MINUTA_GERADA', _('Minuta gerada')
        PROCESSO_CONCLUIDO = 'PROCESSO_CONCLUIDO', _('Processo concluido')

    prestador = models.OneToOneField(
        PrestadorEmpresa,
        on_delete=models.CASCADE,
        related_name='processo_homologacao',
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CADASTRO_INICIADO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Processo de Homologacao'
        verbose_name_plural = 'Processos de Homologacao'
        ordering = ('-criado_em',)

    def __str__(self):
        return f'{self.prestador.razao_social} - {self.status}'

    def registrar_evento(self, acao, descricao='', usuario=None, metadados=None):
        return HistoricoProcesso.objects.create(
            processo=self,
            acao=acao,
            descricao=descricao,
            usuario=usuario,
            metadados=metadados or {},
        )

    def atualizar_status_por_documentos(self, usuario=None):
        documentos_obrigatorios = TipoDocumento.objects.filter(ativo=True, obrigatorio=True)
        documentos_enviados = self.documentos.exclude(
            status__in=(
                DocumentoPrestador.Status.REPROVADO,
                DocumentoPrestador.Status.SUBSTITUIDO,
            )
        ).values_list('tipo_documento_id', flat=True).distinct()
        pendencias = documentos_obrigatorios.exclude(id__in=documentos_enviados)
        novo_status = (
            self.Status.DOCUMENTACAO_PENDENTE
            if pendencias.exists()
            else self.Status.EM_VALIDACAO
        )

        if self.status != novo_status:
            status_anterior = self.status
            self.status = novo_status
            self.save(update_fields=('status', 'atualizado_em'))
            self.registrar_evento(
                acao='Status atualizado',
                descricao=f'Status alterado de {status_anterior} para {novo_status}.',
                usuario=usuario,
                metadados={'status_anterior': status_anterior, 'status_atual': novo_status},
            )


class HistoricoProcesso(models.Model):
    processo = models.ForeignKey(
        ProcessoHomologacao,
        on_delete=models.CASCADE,
        related_name='historico',
    )
    acao = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='eventos_processo',
        blank=True,
        null=True,
    )
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historico do Processo'
        verbose_name_plural = 'Historicos dos Processos'
        ordering = ('-criado_em',)

    def __str__(self):
        return f'{self.processo_id} - {self.acao}'


class FluxoAprovacao(models.Model):
    class Status(models.TextChoices):
        EM_ANDAMENTO = 'EM_ANDAMENTO', _('Em andamento')
        CONCLUIDO = 'CONCLUIDO', _('Concluido')
        ENCERRADO = 'ENCERRADO', _('Encerrado')

    processo = models.OneToOneField(
        ProcessoHomologacao,
        on_delete=models.CASCADE,
        related_name='fluxo_aprovacao',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EM_ANDAMENTO,
    )
    iniciado_em = models.DateTimeField(auto_now_add=True)
    encerrado_em = models.DateTimeField(blank=True, null=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fluxo de Aprovacao'
        verbose_name_plural = 'Fluxos de Aprovacao'
        ordering = ('-iniciado_em',)

    def __str__(self):
        return f'Fluxo do processo {self.processo_id}'


class EtapaAprovacao(models.Model):
    class Status(models.TextChoices):
        AGUARDANDO = 'AGUARDANDO', _('Aguardando')
        LIBERADO = 'LIBERADO', _('Liberado')
        CONCLUIDO = 'CONCLUIDO', _('Concluido')

    fluxo = models.ForeignKey(
        FluxoAprovacao,
        on_delete=models.CASCADE,
        related_name='etapas',
    )
    aprovador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='etapas_aprovacao',
    )
    ordem = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AGUARDANDO,
    )
    data_liberacao = models.DateTimeField(blank=True, null=True)
    data_conclusao = models.DateTimeField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Etapa de Aprovacao'
        verbose_name_plural = 'Etapas de Aprovacao'
        ordering = ('ordem',)
        constraints = [
            models.UniqueConstraint(fields=('fluxo', 'ordem'), name='unique_ordem_por_fluxo'),
            models.UniqueConstraint(fields=('fluxo', 'aprovador'), name='unique_aprovador_por_fluxo'),
        ]

    def __str__(self):
        return f'{self.fluxo_id} - {self.ordem} - {self.aprovador.email}'


class ParecerProcesso(models.Model):
    class Decisao(models.TextChoices):
        APROVADO = 'APROVADO', _('Aprovado')
        REPROVADO = 'REPROVADO', _('Reprovado')

    processo = models.ForeignKey(
        ProcessoHomologacao,
        on_delete=models.CASCADE,
        related_name='pareceres',
    )
    aprovador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pareceres_emitidos',
    )
    etapa = models.OneToOneField(
        EtapaAprovacao,
        on_delete=models.SET_NULL,
        related_name='parecer',
        blank=True,
        null=True,
    )
    decisao = models.CharField(max_length=20, choices=Decisao.choices)
    observacoes = models.TextField(blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    docusign_envelope_id = models.CharField(max_length=255, blank=True, null=True)
    docusign_recipient_id = models.CharField(max_length=255, blank=True, null=True)
    docusign_status = models.CharField(max_length=100, blank=True, null=True)
    docusign_assinado_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Parecer do Processo'
        verbose_name_plural = 'Pareceres dos Processos'
        ordering = ('data_hora',)

    def __str__(self):
        return f'{self.processo_id} - {self.aprovador.email} - {self.decisao}'


class ConfiguracaoFluxoPadrao(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuracao de Fluxo Padrao'
        verbose_name_plural = 'Configuracoes de Fluxo Padrao'
        ordering = ('nome',)

    def __str__(self):
        return self.nome


class EtapaConfiguracaoPadrao(models.Model):
    configuracao = models.ForeignKey(
        ConfiguracaoFluxoPadrao,
        on_delete=models.CASCADE,
        related_name='etapas',
    )
    aprovador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='etapas_configuracao_padrao',
    )
    ordem = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Etapa de Configuracao Padrao'
        verbose_name_plural = 'Etapas de Configuracao Padrao'
        ordering = ('ordem',)
        constraints = [
            models.UniqueConstraint(fields=('configuracao', 'ordem'), name='unique_ordem_por_configuracao_fluxo'),
            models.UniqueConstraint(fields=('configuracao', 'aprovador'), name='unique_aprovador_por_configuracao_fluxo'),
        ]

    def __str__(self):
        return f'{self.configuracao_id} - {self.ordem} - {self.aprovador.email}'


class DocumentoPrestador(models.Model):
    class Status(models.TextChoices):
        ENVIADO = 'ENVIADO', _('Enviado')
        EM_VALIDACAO = 'EM_VALIDACAO', _('Em validacao')
        APROVADO = 'APROVADO', _('Aprovado')
        REPROVADO = 'REPROVADO', _('Reprovado')
        SUBSTITUIDO = 'SUBSTITUIDO', _('Substituido')

    prestador = models.ForeignKey(
        PrestadorEmpresa,
        on_delete=models.CASCADE,
        related_name='documentos',
    )
    processo = models.ForeignKey(
        ProcessoHomologacao,
        on_delete=models.CASCADE,
        related_name='documentos',
    )
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        related_name='documentos_prestadores',
    )
    arquivo = models.FileField(upload_to='documentos/')
    content_type = models.CharField(max_length=100)
    tamanho_bytes = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ENVIADO,
    )
    versao = models.PositiveIntegerField(default=1)
    documento_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='documentos_substitutos',
        blank=True,
        null=True,
    )
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='documentos_validados',
        blank=True,
        null=True,
    )
    validado_em = models.DateTimeField(blank=True, null=True)
    motivo_reprovacao = models.TextField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Documento do Prestador'
        verbose_name_plural = 'Documentos dos Prestadores'
        ordering = ('-enviado_em',)

    def __str__(self):
        return f'{self.prestador.razao_social} - {self.tipo_documento.nome}'
