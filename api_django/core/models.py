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
