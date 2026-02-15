from django.db import models
from django.conf import settings
from django.utils import timezone


class Subscription(models.Model):
    """Modelo de assinatura do usuário"""
    
    STATUS_CHOICES = [
        ('active', 'Ativa'),
        ('pending', 'Pendente'),
        ('canceled', 'Cancelada'),
        ('expired', 'Expirada'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='Usuário'
    )
    kirvano_subscription_id = models.CharField(
        'ID Assinatura Kirvano',
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    plan_name = models.CharField('Nome do Plano', max_length=100)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    start_date = models.DateTimeField('Data de Início', null=True, blank=True)
    expire_date = models.DateTimeField('Data de Expiração', null=True, blank=True)
    notified_expiration_warning = models.BooleanField('Notificado sobre Expiração', default=False)
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.email} - {self.plan_name} ({self.get_status_display()})'
    
    @property
    def is_active(self):
        """Verifica se a assinatura está ativa"""
        if self.status != 'active':
            return False
        if self.expire_date and self.expire_date < timezone.now():
            return False
        return True
    
    def activate(self, start_date=None, expire_date=None):
        """Ativa a assinatura"""
        self.status = 'active'
        self.start_date = start_date or timezone.now()
        if expire_date:
            self.expire_date = expire_date
        self.save()
    
    def cancel(self):
        """Cancela a assinatura"""
        self.status = 'canceled'
        self.save()
    
    def expire(self):
        """Expira a assinatura"""
        self.status = 'expired'
        self.save()
