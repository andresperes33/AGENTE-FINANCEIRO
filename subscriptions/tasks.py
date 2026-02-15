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
        print(f"Suceso: {count} assinaturas marcadas como expiradas em {now}")
    
    return count
