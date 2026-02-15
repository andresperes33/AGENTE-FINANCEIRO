from celery import shared_task
from django.utils import timezone
from .models import Subscription

@shared_task
def check_expired_subscriptions():
    """
    Verifica assinaturas que passaram da data de expiração e atualiza o status para 'expired'
    """
    now = timezone.now()
    expired_subs = Subscription.objects.filter(
        status='active',
        expire_date__lt=now
    )
    
    count = expired_subs.count()
    if count > 0:
        expired_subs.update(status='expired')
        print(f"Sucesso: {count} assinaturas marcadas como expiradas em {now}")
    
    return count

@shared_task
def send_expiration_warnings():
    """
    Notifica usuários cujas assinaturas expiram em 24-26 horas
    """
    from whatsapp_messages.services import EvolutionService
    from agents.services import AIAgentService
    from datetime import timedelta
    
    now = timezone.now()
    warning_threshold = now + timedelta(days=1)
    
    # Busca assinaturas que vencem em 24h e ainda não foram notificadas
    upcoming_expiration = Subscription.objects.filter(
        status='active',
        expire_date__lte=warning_threshold + timedelta(hours=2), # Janela de 2h para garantir captura
        expire_date__gte=warning_threshold,
        notified_expiration_warning=False
    )
    
    if not upcoming_expiration.exists():
        return 0
        
    whatsapp = EvolutionService()
    ai_agent = AIAgentService()
    count = 0
    
    for sub in upcoming_expiration:
        # Pede para a IA gerar um texto de renovação amigável
        ai_prompt = f"Você é o Agente Financeiro. Escreva uma mensagem amigável e humana para o WhatsApp avisando o usuário que sua assinatura '{sub.plan_name}' vence amanhã. Incentive-o a renovar para não perder o controle financeiro. Use emojis. Não seja chato, seja um assistente prestativo."
        msg = ai_agent.gen_notification_text(ai_prompt)
        
        if whatsapp.send_message(sub.user.telefone, msg):
            sub.notified_expiration_warning = True
            sub.save()
            count += 1
            
    return count
