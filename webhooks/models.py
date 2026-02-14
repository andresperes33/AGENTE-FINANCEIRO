from django.db import models
import json


class WebhookEvent(models.Model):
    """Modelo para rastrear eventos de webhooks"""
    
    SOURCE_CHOICES = [
        ('kirvano', 'Kirvano'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    source = models.CharField(
        'Origem',
        max_length=20,
        choices=SOURCE_CHOICES
    )
    event_id = models.CharField(
        'ID do Evento',
        max_length=255,
        unique=True,
        help_text='ID único do evento para evitar duplicação'
    )
    event_type = models.CharField('Tipo de Evento', max_length=100)
    
    # Dados do evento
    payload = models.JSONField('Payload', default=dict)
    headers = models.JSONField('Headers', default=dict, blank=True)
    
    # Status do processamento
    processed = models.BooleanField('Processado', default=False)
    processing_error = models.TextField('Erro de Processamento', blank=True)
    
    # Metadados
    created_at = models.DateTimeField('Recebido em', auto_now_add=True)
    processed_at = models.DateTimeField('Processado em', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Evento de Webhook'
        verbose_name_plural = 'Eventos de Webhooks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', '-created_at']),
            models.Index(fields=['event_id']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f'{self.source} - {self.event_type} - {self.event_id}'
    
    def mark_processed(self):
        """Marca o evento como processado"""
        from django.utils import timezone
        self.processed = True
        self.processed_at = timezone.now()
        self.save()
    
    def mark_error(self, error_message):
        """Marca o evento com erro"""
        from django.utils import timezone
        self.processed = True
        self.processing_error = error_message
        self.processed_at = timezone.now()
        self.save()
    
    @classmethod
    def is_duplicate(cls, event_id):
        """Verifica se o evento já foi recebido"""
        return cls.objects.filter(event_id=event_id).exists()
