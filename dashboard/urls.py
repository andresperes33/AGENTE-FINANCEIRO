from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Transações
    path('transacoes/', views.transactions_list, name='transactions_list'),
    path('transacoes/criar/', views.transaction_create, name='transaction_create'),
    path('transacoes/<int:pk>/editar/', views.transaction_edit, name='transaction_edit'),
    path('transacoes/<int:pk>/deletar/', views.transaction_delete, name='transaction_delete'),
    
    # Relatórios
    path('relatorios/', views.reports, name='reports'),
    
    # Assinatura
    path('assinatura/', views.subscription_detail, name='subscription'),
    
    # Perfil
    path('perfil/', views.profile, name='profile'),
    
    # Exportação
    path('exportar/excel/', views.export_excel, name='export_excel'),
    path('exportar/pdf/', views.export_pdf, name='export_pdf'),
]
