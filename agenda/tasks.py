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
        local_time = timezone.localtime(appt.date_time).strftime('%H:%M')
        ai_prompt = f"Você é o Agente Financeiro. Escreva um lembrete amigável, humano e curto para o WhatsApp avisando que o usuário tem um compromisso chamado '{appt.title}' em 1 hora (às {local_time}). Use alguns emojis. Não adicione nada além do lembrete."
        msg = ai_agent.gen_notification_text(ai_prompt)
        
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
        local_time = timezone.localtime(appt.date_time).strftime('%H:%M')
        ai_prompt = f"Você é o Agente Financeiro. Escreva um lembrete URGENTE, humano e muito rápido para o WhatsApp avisando que o compromisso '{appt.title}' começa em APENAS 5 MINUTOS (às {local_time}). Use emojis de pressa. Seja direto."
        msg = ai_agent.gen_notification_text(ai_prompt)
        
        if whatsapp.send_message(appt.user.telefone, msg):
            appt.notified_5min = True
            appt.save()
