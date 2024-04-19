# coding=UTF-8

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from vol.models import ProcessoSeletivo, StatusProcessoSeletivo, StatusParticipacaoEmProcessoSeletivo, Entidade

from notification.models import Message
from notification.utils import notify_user_msg

class Command(BaseCommand):
    '''Linha de comando para ser colocado para rodar no cron todos os dias logo após a meia-noite.'''
    help = u"Encerra processos seletivos cujo limite de inscrições já passou mas que ainda se encontram ABERTO_A_INSCRICOES, bem como abre para inscrições processos seletivos cujo início de inscrições já começõu mas que ainda se encontram AGUARDANDO_PUBLICACAO."
    usage_str = "Uso: ./manage.py atualizar_processos_seletivos"

    @transaction.atomic
    def handle(self, *args, **options):

        # Encerra processos em aberto cujo limite de inscrições já tenha passado
        processos_em_aberto = ProcessoSeletivo.objects.filter(status=StatusProcessoSeletivo.ABERTO_A_INSCRICOES, limite_inscricoes__lt=timezone.now())

        i = 0

        msg = Message.objects.get(code='AVISO_ENCERRAMENTO_INSCRICOES_SELECAO_V1')
        for processo in processos_em_aberto:
            processo.encerrar_inscricoes()
            processo.save()
            notify_user_msg(processo.cadastrado_por, msg, context={'processo': processo})
            i = i + 1

        self.stdout.write(self.style.NOTICE(str(i) + ' processo(s) seletivo(s) encerrado(s).'))

        # Publica processos após a data de abertura das inscrições 
        processos_nao_iniciados = ProcessoSeletivo.objects.filter(status=StatusProcessoSeletivo.AGUARDANDO_PUBLICACAO, inicio_inscricoes__lt=timezone.now())

        i = 0

        msg = Message.objects.get(code='AVISO_INSCRICOES_INICIADAS_SELECAO_V1')
        for processo in processos_nao_iniciados:
            processo.publicar()
            processo.save()
            notify_user_msg(processo.cadastrado_por, msg, context={'processo': processo})
            i = i + 1

        self.stdout.write(self.style.NOTICE(str(i) + ' processo(s) seletivo(s) iniciado(s).'))

        # Notifica entidades sobre novas inscrições
        entidades_com_processos_em_aberto = Entidade.objects.filter(processoseletivo_set__status=StatusProcessoSeletivo.ABERTO_A_INSCRICOES)

        current_tz = timezone.get_current_timezone()
        now = timezone.now().astimezone(current_tz)

        i = 0

        msg_novas_inscricoes = Message.objects.get(code='AVISO_NOVAS_INSCRICOES_V1')
        for entidade in entidades_com_processos_em_aberto:

            if entidade.ultimo_aviso_proc is not None:

                delta = now - entidade.ultimo_aviso_proc

                if delta.days < 7:
                    # Evitamos notificar novamente entidades que já receberam
                    # essa notificação nos últimos 7 dias
                    continue

            novas_inscricoes = ParticipacaoEmProcessoSeletivo.objects.filter(processoseletivo__entidade=entidade, processoseletivo__status=StatusProcessoSeletivo.ABERTO_A_INSCRICOES, status=StatusParticipacaoEmProcessoSeletivo.AGUARDANDO_SELECAO)

            if entidade.ultimo_acesso_proc is not None:
                # Somente inscrições feitas após o último acesso da entidade na
                # interface de processos são contabilizadas aqui
                novas_inscricoes = novas_inscricoes.filter(data_inscricao__gt=entidade.ultimo_acesso_proc)

            if entidade.ultimo_aviso_proc is not None:
                # Somente inscrições feitas após a última notificação
                # são contabilizadas aqui
                novas_inscricoes = novas_inscricoes.filter(data_inscricao__gt=entidade.ultimo_aviso_proc)

            qtde_novas_inscricoes = novas_inscricoes.count()

            usuario_para_notificacoes = entidade.usuario_para_notificacoes()

            if qtde_novas_inscricoes > 0 and usuario_para_notificacoes:
                notify_user_msg(usuario_para_notificacoes, msg_novas_inscricoes, context={'entidade': entidade, 'link_processos_seletivos_entidade': reverse('processos_seletivos_entidade', kwargs={'id_entidade': entidade.id})})
                entidade.ultimo_aviso_proc = timezone.now()
                entidade.save(update_fields=['ultimo_aviso_proc'])
                i = i + 1

        self.stdout.write(self.style.NOTICE(str(i) + ' entidade(s) notificada(s) sobre novas inscrições em processos seletivos.'))
