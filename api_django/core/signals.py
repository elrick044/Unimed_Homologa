from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProcessoHomologacao
from .services import gerar_minuta_para_processo, iniciar_fluxo_se_em_aprovacao_interna


@receiver(post_save, sender=ProcessoHomologacao)
def processo_status_aprovacao_interna(sender, instance, **kwargs):
    iniciar_fluxo_se_em_aprovacao_interna(instance)
    gerar_minuta_para_processo(instance)
