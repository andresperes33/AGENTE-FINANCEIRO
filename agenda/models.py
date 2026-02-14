from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string

def generate_agenda_identifier():
    """Gera um identificador único para o agendamento (Ex: AG12)"""
    chars = string.ascii_uppercase + string.digits
    return 'AG' + ''.join(random.choices(chars, k=2))

class Appointment(models.Model):
    """Modelo para agenda eletrônica / compromissos"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name='Usuário'
    )
    
    identifier = models.CharField(
        'Identificador',
        max_length=10,
        unique=True,
        default=generate_agenda_identifier
    )
    
    title = models.CharField('Título/Compromisso', max_length=255)
    date_time = models.DateTimeField('Data e Hora')
    
    # Flags para controle de follow-ups
    notified_1h = models.BooleanField('Notificado 1h Antes', default=False)
    notified_5min = models.BooleanField('Notificado 5min Antes', default=False)
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        verbose_name = 'Compromisso'
        verbose_name_plural = 'Compromissos'
        ordering = ['date_time']
        indexes = [
            models.Index(fields=['user', 'date_time']),
            models.Index(fields=['notified_1h', 'notified_5min']),
        ]
    
    def __str__(self):
        return f'{self.identifier} - {self.title} ({self.date_time.strftime("%d/%m/%Y %H:%M")})'

    def save(self, *args, **kwargs):
        if not self.identifier:
            self.identifier = generate_agenda_identifier()
        while Appointment.objects.filter(identifier=self.identifier).exclude(pk=self.pk).exists():
            self.identifier = generate_agenda_identifier()
        super().save(*args, **kwargs)
