from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import DocumentoPrestador, HistoricoProcesso, PrestadorEmpresa, ProcessoHomologacao, TipoDocumento, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informacoes pessoais', {'fields': ('first_name', 'last_name', 'perfil')}),
        ('Permissoes', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'perfil', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'perfil', 'is_staff', 'is_active')
    list_filter = ('perfil', 'is_staff', 'is_superuser', 'is_active')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')


@admin.register(PrestadorEmpresa)
class PrestadorEmpresaAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'cnpj', 'email', 'telefone', 'criado_em')
    search_fields = ('razao_social', 'nome_fantasia', 'cnpj', 'email')


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'obrigatorio', 'ativo', 'criado_em')
    list_filter = ('obrigatorio', 'ativo')
    search_fields = ('nome', 'descricao')


@admin.register(DocumentoPrestador)
class DocumentoPrestadorAdmin(admin.ModelAdmin):
    list_display = ('prestador', 'processo', 'tipo_documento', 'content_type', 'tamanho_bytes', 'enviado_em')
    list_filter = ('tipo_documento', 'content_type', 'enviado_em')
    search_fields = ('prestador__razao_social', 'prestador__cnpj', 'tipo_documento__nome')


class HistoricoProcessoInline(admin.TabularInline):
    model = HistoricoProcesso
    extra = 0
    readonly_fields = ('acao', 'descricao', 'usuario', 'metadados', 'criado_em')
    can_delete = False


@admin.register(ProcessoHomologacao)
class ProcessoHomologacaoAdmin(admin.ModelAdmin):
    list_display = ('prestador', 'status', 'criado_em', 'atualizado_em', 'concluido_em')
    list_filter = ('status', 'criado_em', 'atualizado_em')
    search_fields = ('prestador__razao_social', 'prestador__cnpj')
    inlines = (HistoricoProcessoInline,)


@admin.register(HistoricoProcesso)
class HistoricoProcessoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'acao', 'usuario', 'criado_em')
    list_filter = ('acao', 'criado_em')
    search_fields = ('processo__prestador__razao_social', 'acao', 'descricao')
