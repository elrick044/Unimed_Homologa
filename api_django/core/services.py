from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import EtapaAprovacao, FluxoAprovacao, ParecerProcesso, ProcessoHomologacao, User


def get_aprovadores_padrao():
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
