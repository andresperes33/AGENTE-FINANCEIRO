from django.contrib import admin
from .models import Transaction, TransactionLog


class TransactionLogInline(admin.TabularInline):
    """Inline para exibir logs de transação"""
    model = TransactionLog
    extra = 0
    readonly_fields = ['field_name', 'old_value', 'new_value', 'timestamp']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin para o modelo Transaction"""
    
    list_display = ['identifier', 'user', 'description', 'category', 'amount', 'type', 'transaction_date']
    list_filter = ['type', 'category', 'transaction_date', 'created_at']
    search_fields = ['identifier', 'description', 'user__email', 'user__nome']
    readonly_fields = ['identifier', 'created_at', 'updated_at']
    date_hierarchy = 'transaction_date'
    
    inlines = [TransactionLogInline]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'identifier', 'description', 'category')
        }),
        ('Valores', {
            'fields': ('amount', 'type', 'transaction_date')
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    """Admin para o modelo TransactionLog"""
    
    list_display = ['transaction', 'field_name', 'old_value', 'new_value', 'timestamp']
    list_filter = ['field_name', 'timestamp']
    search_fields = ['transaction__identifier', 'transaction__description']
    readonly_fields = ['transaction', 'field_name', 'old_value', 'new_value', 'timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
