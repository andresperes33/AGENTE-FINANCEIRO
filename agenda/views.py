from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Appointment
from datetime import datetime

@login_required
def appointment_list(request):
    """Lista compromissos do usuário"""
    appointments = Appointment.objects.filter(user=request.user).order_by('date_time')
    return render(request, 'agenda/list.html', {'appointments': appointments})

@login_required
def appointment_create(request):
    """Cria novo compromisso via Dashboard"""
    if request.method == 'POST':
        title = request.POST.get('title')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        
        try:
            if date_str and time_str:
                dt_str = f"{date_str} {time_str}"
                naive_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                dt_obj = timezone.make_aware(naive_dt)
                
                Appointment.objects.create(
                    user=request.user,
                    title=title,
                    date_time=dt_obj
                )
                messages.success(request, 'Compromisso agendado com sucesso!')
                return redirect('agenda:list')
            else:
                messages.error(request, 'Data e hora são obrigatórios.')
        except Exception as e:
            messages.error(request, f'Erro ao agendar: {e}')
            
    return render(request, 'agenda/form.html', {
        'today_iso': timezone.now().date().isoformat()
    })

@login_required
def appointment_edit(request, pk):
    """Edita um compromisso"""
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)
    
    if request.method == 'POST':
        appt.title = request.POST.get('title')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        
        try:
            if date_str and time_str:
                dt_str = f"{date_str} {time_str}"
                # datetime.strptime retorna um objeto naive
                naive_dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                # Converte para aware usando o timezone atual
                dt_obj = timezone.make_aware(naive_dt)
                appt.date_time = dt_obj
                appt.save()
                messages.success(request, 'Compromisso atualizado!')
                return redirect('agenda:list')
            else:
                messages.error(request, 'Data e hora são obrigatórios.')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar: {e}')
            
    # Prepara dados para o formulário
    date_iso = ""
    time_iso = "09:00"
    if appt.date_time:
        # Garante que usamos o horário local para exibir no input
        local_dt = timezone.localtime(appt.date_time)
        date_iso = local_dt.date().isoformat()
        time_iso = local_dt.strftime('%H:%M')
        
    return render(request, 'agenda/form.html', {
        'appointment': appt,
        'date_iso': date_iso,
        'time_iso': time_iso,
        'today_iso': timezone.now().date().isoformat()
    })

@login_required
def appointment_delete(request, pk):
    """Deleta um compromisso"""
    appt = get_object_or_404(Appointment, pk=pk, user=request.user)
    appt.delete()
    messages.success(request, 'Compromisso removido!')
    return redirect('agenda:list')
