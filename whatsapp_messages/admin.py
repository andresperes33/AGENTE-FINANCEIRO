from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin para o modelo Message"""
    
    list_display = ['user', 'message_type', 'status', 'intent', 'created_at', 'is_grouped']
    list_filter = ['status', 'message_type', 'intent', 'is_grouped', 'created_at']
    search_fields = ['user__email', 'phone_number', 'sender_name', 'normalized_text']
    readonly_fields = ['created_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informações do Usuário', {
            'fields': ('user', 'phone_number', 'sender_name')
        }),
        ('Conteúdo Original', {
            'fields': ('message_type', 'raw_content', 'media_url')
        }),
        ('Processamento', {
            'fields': ('normalized_text', 'status', 'intent')
        }),
        ('Debounce', {
            'fields': ('debounce_group', 'is_grouped'),
            'classes': ('collapse',)
        }),
        ('Resposta', {
            'fields': ('response_sent',)
        }),
        ('Metadados', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
