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
        documentos_enviados = self.documentos.values_list('tipo_documento_id', flat=True).distinct()
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


class DocumentoPrestador(models.Model):
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
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Documento do Prestador'
        verbose_name_plural = 'Documentos dos Prestadores'
        ordering = ('-enviado_em',)

    def __str__(self):
        return f'{self.prestador.razao_social} - {self.tipo_documento.nome}'
