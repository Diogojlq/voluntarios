# coding=UTF-8

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from vol.models import ProcessoSeletivo, StatusProcessoSeletivo

class Command(BaseCommand):
    '''Linha de comando para ser colocado para rodar no cron todos os dias logo após a meia-noite.'''
    help = u"Encerra processos seletivos cujo limite de inscrições já passou mas que ainda se encontram ABERTO_A_INSCRICOES."
    usage_str = "Uso: ./manage.py encerrar_processos_seletivos_vencidos"

    @transaction.atomic
    def handle(self, *args, **options):

        processos_em_aberto = ProcessoSeletivo.objects.filter(status=StatusProcessoSeletivo.ABERTO_A_INSCRICOES, limite_inscricoes__lt=timezone.now())

        i = 0

        for processo in processos:
            processo.encerrar_inscricoes()
            processo.save()
            i = i + 1

        self.stdout.write(self.style.INFO(str(i) + ' processo(s) seletivo(s) encerrado(s).'))