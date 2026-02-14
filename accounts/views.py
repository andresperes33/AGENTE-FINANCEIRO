from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponse
from .models import User


def activate_account(request, token):
    """
    View para ativação de conta
    
    O usuário recebe um link via WhatsApp após a compra
    Aqui ele cria sua senha e ativa a conta
    """
    # TODO: Implementar validação de token
    # Por enquanto, vamos usar um sistema simples
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if password != password_confirm:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'accounts/activate.html')
        
        try:
            user = User.objects.get(email=email, is_active=False)
            user.set_password(password)
            user.is_active = True
            user.save()
            
            # Ativar assinatura
            if hasattr(user, 'subscription'):
                user.subscription.activate()
            
            # Fazer login automático
            login(request, user)
            
            messages.success(request, 'Conta ativada com sucesso! Bem-vindo!')
            return redirect('dashboard:home')
            
        except User.DoesNotExist:
            messages.error(request, 'Usuário não encontrado ou já ativado.')
            return render(request, 'accounts/activate.html')
    
    return render(request, 'accounts/activate.html', {'token': token})
