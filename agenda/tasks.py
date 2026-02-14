from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Appointment
from whatsapp_messages.services import EvolutionService

@shared_task
def check_appointment_notifications():
    """
    Verifica compromissos que precisam de notificação (1h antes e 5min antes)
    """
    now = timezone.now()
    whatsapp = EvolutionService()
    
    # 1. Notificação de 1 hora antes (janela de 1h a 1h e 5min para evitar spam se rodar cada minuto)
    # Na verdade, basta verificar se falta menos de 1h e ainda não foi notificado.
    upcoming_1h = Appointment.objects.filter(
        date_time__lte=now + timedelta(hours=1),
        date_time__gt=now,
        notified_1h=False
    )
    
    for appt in upcoming_1h:
        msg = f" ⏰ *Lembrete:* Você tem um compromisso em 1 hora!\n📌 *{appt.title}*\n📅 Horário: {appt.date_time.strftime('%H:%M')}"
        if whatsapp.send_message(appt.user.telefone, msg):
            appt.notified_1h = True
            appt.save()

    # 2. Notificação de 5 minutos antes
    upcoming_5min = Appointment.objects.filter(
        date_time__lte=now + timedelta(minutes=5),
        date_time__gt=now,
        notified_5min=False
    )
    
    for appt in upcoming_5min:
        msg = f" 🚨 *Em 5 minutos!* \nSeu compromisso *{appt.title}* começa às {appt.date_time.strftime('%H:%M')}. Não se atrase!"
        if whatsapp.send_message(appt.user.telefone, msg):
            appt.notified_5min = True
            appt.save()
