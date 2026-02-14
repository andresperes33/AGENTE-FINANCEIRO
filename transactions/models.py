from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string


def generate_identifier():
    """Gera um identificador único para a transação (A1B2)"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=4))



class Transaction(models.Model):
    """Modelo de transação financeira"""
    
    TYPE_CHOICES = [
        ('income', 'Receita'),
        ('expense', 'Despesa'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Usuário'
    )
    identifier = models.CharField(
        'Identificador',
        max_length=20,
        unique=True,
        default=generate_identifier
    )
    description = models.CharField('Descrição', max_length=255)
    category = models.CharField('Categoria', max_length=100)
    amount = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    type = models.CharField(
        'Tipo',
        max_length=10,
        choices=TYPE_CHOICES
    )
    transaction_date = models.DateField('Data da Transação', default=timezone.now)
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', '-transaction_date']),
            models.Index(fields=['user', 'type']),
        ]
    
    def __str__(self):
        return f'{self.identifier} - {self.description} - R$ {self.amount}'
    
    def save(self, *args, **kwargs):
        """Garante que o identifier seja único"""
        if not self.identifier:
            self.identifier = generate_identifier()
        
        # Garante unicidade do identifier
        while Transaction.objects.filter(identifier=self.identifier).exclude(pk=self.pk).exists():
            self.identifier = generate_identifier()
        
        super().save(*args, **kwargs)


class TransactionLog(models.Model):
    """Modelo de log de alterações de transações"""
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='Transação'
    )
    field_name = models.CharField('Campo Alterado', max_length=100)
    old_value = models.TextField('Valor Antigo', blank=True, null=True)
    new_value = models.TextField('Valor Novo', blank=True, null=True)
    
    timestamp = models.DateTimeField('Data/Hora', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Transação'
        verbose_name_plural = 'Logs de Transações'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f'{self.transaction.identifier} - {self.field_name} alterado em {self.timestamp}'
