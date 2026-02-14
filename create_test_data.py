import os
import django
from django.utils import timezone
from datetime import timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from transactions.models import Transaction
from subscriptions.models import Subscription

User = get_user_model()

def create_data():
    # 1. Criar Usuário Demo
    email = 'usuario@teste.com'
    if not User.objects.filter(email=email).exists():
        user = User.objects.create_user(
            email=email,
            telefone='5511999998888',
            nome='Usuário Demo',
            password='senha123'
        )
        print(f"Usuário criado: {email} / senha123")
    else:
        user = User.objects.get(email=email)
        print(f"Usuário existente: {email}")

    # 2. Criar Assinatura
    if not hasattr(user, 'subscription'):
        Subscription.objects.create(
            user=user,
            plan_name='Premium',
            status='active',
            start_date=timezone.now() - timedelta(days=30),
            expire_date=timezone.now() + timedelta(days=30),
            kirvano_subscription_id='sub_123456'
        )
        print("Assinatura criada/ativada.")
    
    # 3. Criar Transações (30 dias)
    categories = ['Alimentação', 'Transporte', 'Moradia', 'Lazer', 'Saúde', 'Salário', 'Investimentos']
    
    # Limpar transações antigas deste user para não duplicar
    Transaction.objects.filter(user=user).delete()
    
    # Salário (Receita)
    Transaction.objects.create(
        user=user,
        description='Salário Mensal',
        amount=5000.00,
        type='income',
        category='Salário',
        transaction_date=timezone.now().date().replace(day=5)
    )
    
    # Freela (Receita)
    Transaction.objects.create(
        user=user,
        description='Projeto Extra',
        amount=1200.00,
        type='income',
        category='Salário',
        transaction_date=timezone.now().date().replace(day=20)
    )
    
    # Despesas aleatórias
    for i in range(15):
        days_ago = random.randint(0, 30)
        date = timezone.now().date() - timedelta(days=days_ago)
        category = random.choice(categories)
        amount = random.uniform(20.0, 300.0)
        
        Transaction.objects.create(
            user=user,
            description=f'Gasto com {category}',
            amount=round(amount, 2),
            type='expense',
            category=category,
            transaction_date=date
        )
        
    print(f"Criadas {Transaction.objects.filter(user=user).count()} transações para o usuário.")

if __name__ == '__main__':
    create_data()
