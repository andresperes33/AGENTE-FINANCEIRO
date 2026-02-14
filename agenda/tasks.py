from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Appointment
from whatsapp_messages.services import EvolutionService
from agents.services import AIAgentService

@shared_task
def check_appointment_notifications():
    """
    Verifica compromissos que precisam de notificação e gera o lembrete via IA
    """
    now = timezone.now()
    whatsapp = EvolutionService()
    ai_agent = AIAgentService()
    
    # 1. Notificação de 1 hora antes
    upcoming_1h = Appointment.objects.filter(
        date_time__lte=now + timedelta(hours=1),
        date_time__gt=now + timedelta(minutes=5), # Evita conflito com o de 5min
        notified_1h=False
    )
    
    for appt in upcoming_1h:
        # Pede para a IA gerar um lembrete amigável
        ai_prompt = f"Gere um lembrete amigável e curto para o WhatsApp avisando que o usuário tem um compromisso chamado '{appt.title}' em 1 hora (às {appt.date_time.strftime('%H:%M')}). Use emojis."
        msg = ai_agent.process_message(ai_prompt, appt.user)
        
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
        ai_prompt = f"Gere um lembrete URGENTE e rápido para o WhatsApp avisando que o compromisso '{appt.title}' começa em APENAS 5 MINUTOS (às {appt.date_time.strftime('%H:%M')}). Seja direto e use emojis de pressa."
        msg = ai_agent.process_message(ai_prompt, appt.user)
        
        if whatsapp.send_message(appt.user.telefone, msg):
            appt.notified_5min = True
            appt.save()
