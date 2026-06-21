from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    DocumentoPrestador,
    ConfiguracaoFluxoPadrao,
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
    list_display = ('prestador', 'processo', 'tipo_documento', 'status', 'versao', 'validado_por', 'validado_em', 'enviado_em')
    list_filter = ('status', 'tipo_documento', 'content_type', 'enviado_em', 'validado_em')
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


class EtapaAprovacaoInline(admin.TabularInline):
    model = EtapaAprovacao
    extra = 0


@admin.register(FluxoAprovacao)
class FluxoAprovacaoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'iniciado_em', 'atualizado_em')
    search_fields = ('processo__prestador__razao_social', 'processo__prestador__cnpj')
    inlines = (EtapaAprovacaoInline,)


@admin.register(EtapaAprovacao)
class EtapaAprovacaoAdmin(admin.ModelAdmin):
    list_display = ('fluxo', 'aprovador', 'ordem', 'status', 'data_liberacao', 'data_conclusao')
    list_filter = ('status', 'data_liberacao', 'data_conclusao')
    search_fields = ('fluxo__processo__prestador__razao_social', 'aprovador__email')


@admin.register(ParecerProcesso)
class ParecerProcessoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'aprovador', 'decisao', 'data_hora')
    list_filter = ('decisao', 'data_hora')
    search_fields = ('processo__prestador__razao_social', 'aprovador__email', 'observacoes')


class EtapaConfiguracaoPadraoInline(admin.TabularInline):
    model = EtapaConfiguracaoPadrao
    extra = 0


@admin.register(ConfiguracaoFluxoPadrao)
class ConfiguracaoFluxoPadraoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo', 'criado_em', 'atualizado_em')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    inlines = (EtapaConfiguracaoPadraoInline,)


@admin.register(EtapaConfiguracaoPadrao)
class EtapaConfiguracaoPadraoAdmin(admin.ModelAdmin):
    list_display = ('configuracao', 'ordem', 'aprovador')
    search_fields = ('configuracao__nome', 'aprovador__email')


@admin.register(TemplateContrato)
class TemplateContratoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'versao', 'ativo', 'template_anterior', 'criado_em', 'atualizado_em')
    list_filter = ('ativo', 'versao')
    search_fields = ('nome', 'conteudo_html')


@admin.register(MinutaContrato)
class MinutaContratoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'template', 'gerado_em')
    list_filter = ('gerado_em', 'template')
    search_fields = ('processo__prestador__razao_social', 'processo__prestador__cnpj', 'template__nome')
