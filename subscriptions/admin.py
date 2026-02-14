from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin para o modelo Subscription"""
    
    list_display = ['user', 'plan_name', 'status', 'start_date', 'expire_date', 'is_active']
    list_filter = ['status', 'plan_name', 'created_at']
    search_fields = ['user__email', 'user__nome', 'kirvano_subscription_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informações do Usuário', {
            'fields': ('user',)
        }),
        ('Informações da Assinatura', {
            'fields': ('plan_name', 'kirvano_subscription_id', 'status')
        }),
        ('Datas', {
            'fields': ('start_date', 'expire_date', 'created_at', 'updated_at')
        }),
    )
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Ativa'
