from django.contrib import admin
from .models import WebhookEvent


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    """Admin para o modelo WebhookEvent"""
    
    list_display = ['event_id', 'source', 'event_type', 'processed', 'created_at']
    list_filter = ['source', 'event_type', 'processed', 'created_at']
    search_fields = ['event_id', 'event_type']
    readonly_fields = ['created_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informações do Evento', {
            'fields': ('source', 'event_id', 'event_type')
        }),
        ('Dados', {
            'fields': ('payload', 'headers')
        }),
        ('Processamento', {
            'fields': ('processed', 'processing_error', 'processed_at')
        }),
        ('Metadados', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Não permite adicionar eventos manualmente"""
        return False
