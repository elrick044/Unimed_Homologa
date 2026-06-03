import re

from django.core.files.base import ContentFile
from django.db import transaction
from django.template import Context, Template
from django.utils.html import strip_tags
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import (
    ConfiguracaoFluxoPadrao,
    EtapaAprovacao,
    FluxoAprovacao,
    MinutaContrato,
    ParecerProcesso,
    ProcessoHomologacao,
    TemplateContrato,
    User,
)


def _escape_pdf_text(value):
    return (value or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _build_simple_pdf(text):
    lines = [line.strip() for line in re.split(r'[\r\n]+', text or '') if line.strip()]
    if not lines:
        lines = ['Minuta de contrato']

    content_lines = ['BT', '/F1 11 Tf', '72 760 Td', '14 TL']
    for index, line in enumerate(lines[:48]):
        if index:
            content_lines.append('T*')
        content_lines.append(f'({_escape_pdf_text(line[:110])}) Tj')
    content_lines.append('ET')
    stream = '\n'.join(content_lines).encode('latin-1', errors='replace')

    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream',
    ]

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode('ascii'))
        pdf.extend(obj)
        pdf.extend(b'\nendobj\n')

    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
    pdf.extend(
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('ascii')
    )
    return bytes(pdf)


def renderizar_html_para_pdf(conteudo_html):
    try:
        from weasyprint import HTML
    except ImportError:
        texto = strip_tags(conteudo_html).replace('&nbsp;', ' ')
        return _build_simple_pdf(texto)

    return HTML(string=conteudo_html).write_pdf()


@transaction.atomic
def gerar_minuta_para_processo(processo):
    if processo.status != ProcessoHomologacao.Status.APROVADO:
        return None

    if MinutaContrato.objects.filter(processo=processo).exists():
        return processo.minuta_contrato

    template = TemplateContrato.objects.filter(ativo=True).order_by('-versao', '-atualizado_em').first()
    if not template:
        return None

    prestador = processo.prestador
    contexto = {
        'razao_social': prestador.razao_social,
        'nome_fantasia': prestador.nome_fantasia,
        'cnpj': prestador.cnpj,
        'endereco': prestador.endereco,
        'nome_responsavel': prestador.nome_responsavel,
        'email': prestador.email,
        'telefone': prestador.telefone,
        'processo_id': processo.id,
    }
    html_renderizado = Template(template.conteudo_html).render(Context(contexto))
    pdf = renderizar_html_para_pdf(html_renderizado)

    minuta = MinutaContrato(processo=processo, template=template)
    minuta.arquivo_pdf.save(f'minuta_processo_{processo.id}.pdf', ContentFile(pdf), save=True)

    status_anterior = processo.status
    processo.status = ProcessoHomologacao.Status.MINUTA_GERADA
    processo.save(update_fields=('status', 'atualizado_em'))
    processo.registrar_evento(
        acao='Minuta gerada',
        descricao='Minuta de contrato gerada automaticamente apos aprovacao final.',
        metadados={
            'status_anterior': status_anterior,
            'status_atual': processo.status,
            'template_id': template.id,
            'template_versao': template.versao,
            'minuta_id': minuta.id,
        },
    )
    return minuta


def get_aprovadores_padrao():
    configuracao = ConfiguracaoFluxoPadrao.objects.filter(ativo=True).prefetch_related(
        'etapas__aprovador',
    ).order_by('-atualizado_em').first()

    if configuracao and configuracao.etapas.exists():
        return [
            etapa.aprovador
            for etapa in configuracao.etapas.select_related('aprovador').order_by('ordem')
            if etapa.aprovador.is_active
        ]

    return User.objects.filter(
        perfil=User.Perfil.EQUIPE_ADMINISTRATIVA,
        is_active=True,
    ).order_by('id')


@transaction.atomic
def criar_fluxo_aprovacao_padrao(processo):
    fluxo, created = FluxoAprovacao.objects.get_or_create(processo=processo)

    if fluxo.etapas.exists():
        return fluxo

    aprovadores = list(get_aprovadores_padrao())
    agora = timezone.now()

    for index, aprovador in enumerate(aprovadores, start=1):
        EtapaAprovacao.objects.create(
            fluxo=fluxo,
            aprovador=aprovador,
            ordem=index,
            status=EtapaAprovacao.Status.LIBERADO if index == 1 else EtapaAprovacao.Status.AGUARDANDO,
            data_liberacao=agora if index == 1 else None,
        )

    if created:
        processo.registrar_evento(
            acao='Fluxo de aprovacao criado',
            descricao='Fluxo de aprovacao interna criado automaticamente.',
            metadados={'total_aprovadores': len(aprovadores)},
        )

    return fluxo


def iniciar_fluxo_se_em_aprovacao_interna(processo):
    if processo.status == ProcessoHomologacao.Status.EM_APROVACAO_INTERNA:
        return criar_fluxo_aprovacao_padrao(processo)

    return None


class ParecerContext:
    def __init__(self, processo, usuario, decisao, observacoes='', logger=None):
        self.processo = processo
        self.usuario = usuario
        self.decisao = decisao
        self.observacoes = observacoes or ''
        self.logger = logger
        self.fluxo = None
        self.etapa_atual = None
        self.proxima_etapa = None
        self.parecer = None


class ParecerHandler:
    def __init__(self, proximo=None):
        self.proximo = proximo

    def handle(self, context):
        self.process(context)
        if self.proximo:
            return self.proximo.handle(context)
        return context

    def process(self, context):
        raise NotImplementedError


class FluxoAbertoHandler(ParecerHandler):
    def process(self, context):
        try:
            context.fluxo = context.processo.fluxo_aprovacao
        except FluxoAprovacao.DoesNotExist:
            raise ValidationError({'processo': ['Processo nao possui fluxo de aprovacao iniciado.']})

        if context.fluxo.status != FluxoAprovacao.Status.EM_ANDAMENTO:
            raise ValidationError({'fluxo': ['Fluxo de aprovacao nao esta em andamento.']})

        if context.processo.status != ProcessoHomologacao.Status.EM_APROVACAO_INTERNA:
            raise ValidationError({'processo': ['Processo nao esta em aprovacao interna.']})


class EtapaLiberadaDoUsuarioHandler(ParecerHandler):
    def process(self, context):
        context.etapa_atual = context.fluxo.etapas.filter(
            aprovador=context.usuario,
            status=EtapaAprovacao.Status.LIBERADO,
        ).order_by('ordem').first()

        if not context.etapa_atual:
            raise PermissionDenied('Usuario nao possui etapa liberada para este processo.')

        etapa_pendente_anterior = context.fluxo.etapas.filter(
            ordem__lt=context.etapa_atual.ordem,
        ).exclude(status=EtapaAprovacao.Status.CONCLUIDO).exists()

        if etapa_pendente_anterior:
            raise ValidationError({'ordem': ['Existem etapas anteriores ainda nao concluidas.']})


class RegistroParecerHandler(ParecerHandler):
    def process(self, context):
        context.parecer = ParecerProcesso.objects.create(
            processo=context.processo,
            aprovador=context.usuario,
            etapa=context.etapa_atual,
            decisao=context.decisao,
            observacoes=context.observacoes,
        )


class TransicaoParecerHandler(ParecerHandler):
    def process(self, context):
        agora = timezone.now()

        if context.decisao == ParecerProcesso.Decisao.REPROVADO:
            context.etapa_atual.status = EtapaAprovacao.Status.CONCLUIDO
            context.etapa_atual.data_conclusao = agora
            context.etapa_atual.save(update_fields=('status', 'data_conclusao', 'atualizado_em'))

            context.fluxo.status = FluxoAprovacao.Status.ENCERRADO
            context.fluxo.encerrado_em = agora
            context.fluxo.save(update_fields=('status', 'encerrado_em', 'atualizado_em'))

            context.processo.status = ProcessoHomologacao.Status.REPROVADO
            context.processo.save(update_fields=('status', 'atualizado_em'))
            context.processo.registrar_evento(
                acao='Processo reprovado',
                descricao='Processo reprovado durante a aprovacao interna.',
                usuario=context.usuario,
                metadados={
                    'parecer_id': context.parecer.id,
                    'etapa_id': context.etapa_atual.id,
                    'motivo': context.observacoes,
                },
            )
            return

        context.etapa_atual.status = EtapaAprovacao.Status.CONCLUIDO
        context.etapa_atual.data_conclusao = agora
        context.etapa_atual.save(update_fields=('status', 'data_conclusao', 'atualizado_em'))

        context.proxima_etapa = context.fluxo.etapas.filter(
            ordem__gt=context.etapa_atual.ordem,
            status=EtapaAprovacao.Status.AGUARDANDO,
        ).order_by('ordem').first()

        if context.proxima_etapa:
            context.proxima_etapa.status = EtapaAprovacao.Status.LIBERADO
            context.proxima_etapa.data_liberacao = agora
            context.proxima_etapa.save(update_fields=('status', 'data_liberacao', 'atualizado_em'))
            context.processo.registrar_evento(
                acao='Etapa de aprovacao liberada',
                descricao=f'Etapa {context.proxima_etapa.ordem} liberada para parecer.',
                usuario=context.usuario,
                metadados={
                    'parecer_id': context.parecer.id,
                    'etapa_concluida_id': context.etapa_atual.id,
                    'proxima_etapa_id': context.proxima_etapa.id,
                },
            )
            return

        context.fluxo.status = FluxoAprovacao.Status.CONCLUIDO
        context.fluxo.encerrado_em = agora
        context.fluxo.save(update_fields=('status', 'encerrado_em', 'atualizado_em'))

        context.processo.status = ProcessoHomologacao.Status.APROVADO
        context.processo.save(update_fields=('status', 'atualizado_em'))
        context.processo.registrar_evento(
            acao='Processo aprovado',
            descricao='Todas as etapas de aprovacao interna foram concluidas.',
            usuario=context.usuario,
            metadados={
                'parecer_id': context.parecer.id,
                'etapa_id': context.etapa_atual.id,
            },
        )


def build_parecer_chain():
    return FluxoAbertoHandler(
        EtapaLiberadaDoUsuarioHandler(
            RegistroParecerHandler(
                TransicaoParecerHandler()
            )
        )
    )


@transaction.atomic
def emitir_parecer_processo(processo, usuario, decisao, observacoes='', logger=None):
    context = ParecerContext(
        processo=processo,
        usuario=usuario,
        decisao=decisao,
        observacoes=observacoes,
        logger=logger,
    )
    return build_parecer_chain().handle(context)
