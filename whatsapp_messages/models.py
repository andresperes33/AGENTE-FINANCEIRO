from django.db import models
from django.conf import settings


class Message(models.Model):
    """Modelo de mensagens do WhatsApp"""
    
    TYPE_CHOICES = [
        ('text', 'Texto'),
        ('audio', 'Áudio'),
        ('image', 'Imagem'),
    ]
    
    STATUS_CHOICES = [
        ('received', 'Recebida'),
        ('processing', 'Processando'),
        ('normalized', 'Normalizada'),
        ('routed', 'Roteada'),
        ('completed', 'Completada'),
        ('error', 'Erro'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Usuário',
        null=True,
        blank=True
    )
    
    # Dados originais
    phone_number = models.CharField('Número de Telefone', max_length=20)
    sender_name = models.CharField('Nome do Remetente', max_length=255, blank=True)
    message_type = models.CharField(
        'Tipo de Mensagem',
        max_length=10,
        choices=TYPE_CHOICES
    )
    raw_content = models.TextField('Conteúdo Original', blank=True)
    media_url = models.URLField('URL da Mídia', blank=True, null=True)
    
    # Conteúdo normalizado
    normalized_text = models.TextField('Texto Normalizado', blank=True)
    
    # Status e processamento
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='received'
    )
    intent = models.CharField('Intenção Identificada', max_length=100, blank=True)
    
    # Debounce - para agrupar mensagens
    debounce_group = models.CharField('Grupo de Debounce', max_length=100, blank=True, null=True)
    is_grouped = models.BooleanField('Agrupada', default=False)
    
    # Resposta
    response_sent = models.TextField('Resposta Enviada', blank=True)
    
    # Metadados
    created_at = models.DateTimeField('Recebida em', auto_now_add=True)
    processed_at = models.DateTimeField('Processada em', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['debounce_group']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else "Desconhecido"
        return f'{user_email} - {self.message_type} - {self.created_at}'
    
    def normalize(self, normalized_text):
        """Normaliza a mensagem"""
        self.normalized_text = normalized_text
        self.status = 'normalized'
        self.save()
    
    def set_intent(self, intent):
        """Define a intenção identificada"""
        self.intent = intent
        self.status = 'routed'
        self.save()
    
    def complete(self, response=''):
        """Marca a mensagem como completada"""
        self.status = 'completed'
        self.response_sent = response
        self.save()
    
    def mark_error(self):
        """Marca a mensagem com erro"""
        self.status = 'error'
        self.save()
