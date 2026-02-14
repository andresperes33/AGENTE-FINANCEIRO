from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta

from transactions.models import Transaction, TransactionLog
from subscriptions.models import Subscription
from .utils import generate_transactions_excel, generate_transactions_pdf


@login_required
def home(request):
    """Dashboard home com resumo financeiro"""
    user = request.user
    today = timezone.now().date()
    
    # Transações do mês atual
    transactions_month = Transaction.objects.filter(
        user=user,
        transaction_date__month=today.month,
        transaction_date__year=today.year
    )
    
    # Cálculos do Mês
    income_month = transactions_month.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    expense_month = transactions_month.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
    
    # Saldo Real (Total de todas as transações)
    all_transactions = Transaction.objects.filter(user=user)
    total_income = all_transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = all_transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
    total_balance = total_income - total_expense
    
    # Gráfico de Rosca: Gastos por Categoria (Mês Atual)
    category_expenses = transactions_month.filter(type='expense').values('category').annotate(total=Sum('amount')).order_by('-total')
    chart_categories = [c['category'] for c in category_expenses]
    chart_category_values = [float(c['total']) for c in category_expenses]

    # Gráfico de Linha: Evolução nos últimos 30 dias
    start_date = today - timedelta(days=30)
    initial_balance = all_transactions.filter(transaction_date__lt=start_date).aggregate(
        inc=Sum('amount', filter=Q(type='income')),
        exp=Sum('amount', filter=Q(type='expense'))
    )
    current_runner = (initial_balance['inc'] or 0) - (initial_balance['exp'] or 0)
    
    daily_stats = all_transactions.filter(transaction_date__gte=start_date).values('transaction_date').annotate(
        day_inc=Sum('amount', filter=Q(type='income')),
        day_exp=Sum('amount', filter=Q(type='expense'))
    ).order_by('transaction_date')
    
    chart_days = []
    chart_balances = []
    for day in daily_stats:
        day_net = (day['day_inc'] or 0) - (day['day_exp'] or 0)
        current_runner += day_net
        chart_days.append(day['transaction_date'].strftime('%d/%m'))
        chart_balances.append(float(current_runner))

    # Últimas transações
    recent_transactions = all_transactions.order_by('-transaction_date', '-created_at')[:5]
    
    context = {
        'income_month': income_month,
        'expense_month': expense_month,
        'balance': total_balance,
        'recent_transactions': recent_transactions,
        'chart_categories': chart_categories,
        'chart_category_values': chart_category_values,
        'chart_days': chart_days,
        'chart_balances': chart_balances,
        'now': timezone.now(),
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
def transactions_list(request):
    """Lista todas as transações"""
    user = request.user
    
    # Filtros
    type_filter = request.GET.get('type')
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    transactions = Transaction.objects.filter(user=user)
    
    if type_filter:
        transactions = transactions.filter(type=type_filter)
    
    if category_filter:
        transactions = transactions.filter(category=category_filter)
    
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    # Categorias únicas para filtro
    categories = Transaction.objects.filter(user=user).values_list('category', flat=True).distinct()
    
    context = {
        'transactions': transactions,
        'categories': categories,
        'type_filter': type_filter,
        'category_filter': category_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'dashboard/transactions_list.html', context)


@login_required
def transaction_create(request):
    """Criar nova transação"""
    if request.method == 'POST':
        description = request.POST.get('description')
        category = request.POST.get('category')
        amount_raw = request.POST.get('amount', '0').replace(',', '.')
        type_tx = request.POST.get('type')
        transaction_date = request.POST.get('transaction_date')
        
        try:
            Transaction.objects.create(
                user=request.user,
                description=description,
                category=category,
                amount=float(amount_raw),
                type=type_tx,
                transaction_date=transaction_date or timezone.now().date()
            )
            messages.success(request, 'Transação criada com sucesso!')
            return redirect('dashboard:transactions_list')
        except Exception as e:
            messages.error(request, f'Erro ao criar transação: {e}')
    
    context = {
        'today_iso': timezone.now().date().isoformat(),
    }
    return render(request, 'dashboard/transaction_form.html', context)


@login_required
def transaction_edit(request, pk):
    """Editar transação"""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Salvar valores antigos para log
        old_values = {
            'description': transaction.description,
            'category': transaction.category,
            'amount': str(transaction.amount),
            'type': transaction.type,
            'transaction_date': str(transaction.transaction_date),
        }
        
        try:
            # Atualizar campos
            transaction.description = request.POST.get('description')
            transaction.category = request.POST.get('category')
            amount_raw = request.POST.get('amount', '0').replace(',', '.')
            transaction.amount = float(amount_raw)
            transaction.type = request.POST.get('type')
            transaction_date = request.POST.get('transaction_date')
            if transaction_date:
                transaction.transaction_date = transaction_date
            
            transaction.save()
            
            # Criar logs de alteração
            for field, old_value in old_values.items():
                new_value = str(getattr(transaction, field))
                if old_value != new_value:
                    TransactionLog.objects.create(
                        transaction=transaction,
                        field_name=field,
                        old_value=old_value,
                        new_value=new_value
                    )
            
            messages.success(request, 'Transação atualizada com sucesso!')
            return redirect('dashboard:transactions_list')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar transação: {e}')
    
    context = {
        'transaction': transaction,
        'today_iso': timezone.now().date().isoformat(),
    }
    return render(request, 'dashboard/transaction_form.html', context)



@login_required
def transaction_delete(request, pk):
    """Deletar transação"""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transação deletada com sucesso!')
        return redirect('dashboard:transactions_list')
    
    context = {'transaction': transaction}
    return render(request, 'dashboard/transaction_confirm_delete.html', context)


@login_required
def reports(request):
    """Relatórios financeiros"""
    user = request.user
    
    # Período
    period = request.GET.get('period', '30')  # dias
    days = int(period)
    
    start_date = timezone.now().date() - timedelta(days=days)
    
    transactions = Transaction.objects.filter(
        user=user,
        transaction_date__gte=start_date
    )
    
    # Por tipo
    income_total = transactions.filter(type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    expense_total = transactions.filter(type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Por categoria
    expenses_by_category = transactions.filter(type='expense').values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    income_by_category = transactions.filter(type='income').values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    context = {
        'period': period,
        'income_total': income_total,
        'expense_total': expense_total,
        'balance': income_total - expense_total,
        'expenses_by_category': expenses_by_category,
        'income_by_category': income_by_category,
        # Dados para Gráficos
        'cash_flow_data': [float(income_total), float(expense_total)],
        'expense_labels': [item['category'] for item in expenses_by_category],
        'expense_data': [float(item['total']) for item in expenses_by_category],
    }
    
    return render(request, 'dashboard/reports.html', context)


@login_required
def subscription_detail(request):
    """Detalhes da assinatura"""
    subscription = get_object_or_404(Subscription, user=request.user)
    
    context = {'subscription': subscription}
    return render(request, 'dashboard/subscription.html', context)


@login_required
def profile(request):
    """Perfil do usuário"""
    user = request.user
    
    if request.method == 'POST':
        user.nome = request.POST.get('nome')
        user.telefone = request.POST.get('telefone')
        
        # Atualizar senha se fornecida
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
            user.must_change_password = False
        
        user.save()

        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('dashboard:profile')
    
    context = {'user': user}
    return render(request, 'dashboard/profile.html', context)

@login_required
def export_excel(request):
    """Exporta transações para Excel"""
    user = request.user
    
    # Filtros (mesma lógica da listagem)
    type_filter = request.GET.get('type')
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    transactions = Transaction.objects.filter(user=user)
    
    if type_filter:
        transactions = transactions.filter(type=type_filter)
    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    output = generate_transactions_excel(transactions)
    
    filename = f"transacoes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response


@login_required
def export_pdf(request):
    """Exporta relatório PDF com gráficos e filtros"""
    user = request.user
    
    # Filtros
    type_filter = request.GET.get('type')
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    period = request.GET.get('period', '30')
    
    transactions = Transaction.objects.filter(user=user)
    
    if type_filter:
        transactions = transactions.filter(type=type_filter)
    if category_filter:
        transactions = transactions.filter(category=category_filter)
        
    if date_from and date_to:
        transactions = transactions.filter(transaction_date__range=[date_from, date_to])
    elif date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    elif date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    else:
        # Se não houver data, usa o período padrão de dias
        days = int(period)
        start_date = timezone.now().date() - timedelta(days=days)
        transactions = transactions.filter(transaction_date__gte=start_date)
    
    transactions = transactions.order_by('-transaction_date')
    
    # Dados para o resumo e gráficos
    income_total = transactions.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expense_total = transactions.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    
    expenses_by_category = transactions.filter(type='expense').values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    summary_data = {
        'income_total': float(income_total),
        'expense_total': float(expense_total),
        'balance': float(income_total - expense_total),
        'expense_labels': [item['category'] for item in expenses_by_category],
        'expense_data': [float(item['total']) for item in expenses_by_category],
        'date_range': f"{date_from or 'Início'} até {date_to or 'Hoje'}" if (date_from or date_to) else f"Últimos {period} dias"
    }
    
    output = generate_transactions_pdf(user, transactions, summary_data)
    
    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(output, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response
