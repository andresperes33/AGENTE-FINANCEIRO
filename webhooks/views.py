from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import json
import hashlib
import hmac
import random
import string
import os
from datetime import timedelta

from .models import WebhookEvent
from subscriptions.models import Subscription
from whatsapp_messages.models import Message
from whatsapp_messages.services import EvolutionService

User = get_user_model()


@csrf_exempt
@require_http_methods(["POST"])
def kirvano_webhook(request):
    try:
        body_unicode = request.body.decode('utf-8')
        payload = json.loads(body_unicode)
        # Tenta capturar de várias formas possíveis (com X-, sem X-, maiúsculo/minúsculo)
        signature = (
            request.headers.get('X-Kirvano-Signature') or 
            request.headers.get('x-kirvano-signature') or
            request.headers.get('Kirvano-Signature') or
            request.headers.get('Signature')
        )
        
        print(f"--- WEBHOOK KIRVANO RECEBIDO ---")
        print(f"Tipo do evento: {payload.get('event_type') or payload.get('type')}")
        print(f"Signature encontrada: {'SIM' if signature else 'AUSENTE'}")

        secret = os.getenv('KIRVANO_WEBHOOK_SECRET') or os.getenv('KIRVANO_WEBHOOK_TOKEN')
        if secret:
            if not validate_kirvano_signature(signature, request.body):
                sig_preview = str(signature)[:10] if signature else "AUSENTE"
                print(f"ERRO DE SEGURANÇA: Assinatura Kirvano Inválida! (Signature recebida: {sig_preview})")
                
                # Se a assinatura for ausente, vamos logar todos os headers para debug
                if not signature:
                    print("Headers recebidos para diagnóstico:")
                    for header, value in request.headers.items():
                        print(f"  {header}: {value}")
                
                return JsonResponse({'error': 'Invalid Signature'}, status=403)
        else:
            print("AVISO CRÍTICO: KIRVANO_WEBHOOK_SECRET não configurado. O sistema está vulnerável.")
            # Para manter compatibilidade se o usuário ainda não configurou, 
            # podemos permitir mas logar o erro. Melhor seria bloquear.
            # Vou bloquear para garantir a segurança solicitada.
            if settings.DEBUG is False:
                 return JsonResponse({'error': 'Webhook Secret Not Configured'}, status=500)

        event_id = payload.get('event_id') or payload.get('id') or f"test_{timezone.now().timestamp()}"
        event_type = payload.get('event_type') or payload.get('type') or 'test'
        
        webhook_event = WebhookEvent.objects.create(
            source='kirvano', 
            event_id=event_id, 
            event_type=event_type, 
            payload=payload, 
            headers=dict(request.headers)
        )
        
        try:
            process_kirvano_event(payload, event_type)
            webhook_event.mark_processed()
        except Exception as e:
            print(f"Erro ao processar evento Kirvano: {str(e)}")
            webhook_event.mark_error(str(e))
            
        return JsonResponse({'status': 'success'}, status=200)
    except Exception as e:
        print(f"Erro Crítico Webhook Kirvano: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def generate_random_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def process_kirvano_event(payload, event_type):
    # 1. TRATAMENTO DE ATIVAÇÃO E RENOVAÇÃO
    if event_type in ['purchase.approved', 'RECURRING', 'SALE_APPROVED', 'SUBSCRIPTION_RENEWED']:
        customer_data = payload.get('customer', {})
        plan_data = payload.get('plan', {})
        
        email = customer_data.get('email')
        phone = customer_data.get('phone') or customer_data.get('phone_number')
        name = customer_data.get('name') or 'Cliente'
        
        if not email: return
            
        user = User.objects.filter(email=email).first()
        temp_password = None
        
        if not user:
            temp_password = generate_random_password()
            user = User.objects.create_user(
                email=email, 
                telefone=phone or f"TEMP_{generate_random_password(4)}", 
                nome=name, 
                password=temp_password
            )
            user.must_change_password = True
            user.save()
            
        sub_id = payload.get('sale_id') or payload.get('id') or (payload.get('subscription') or {}).get('id') or 'TEST_ID'
        plan_name = (plan_data.get('name') or payload.get('plan_name') or 'Assistente Financeiro').lower()

        # Cálculo da data de expiração baseado no plano
        days = 30 # Default
        if 'anual' in plan_name:
            days = 365
        elif 'semestral' in plan_name:
            days = 180
        elif 'trimestral' in plan_name:
            days = 90
        elif 'mensal' in plan_name:
            days = 30
            
        expire_date = timezone.now() + timedelta(days=days)

        Subscription.objects.update_or_create(
            user=user, 
            defaults={
                'kirvano_subscription_id': sub_id, 
                'plan_name': plan_name.capitalize(), 
                'status': 'active', 
                'start_date': timezone.now(),
                'expire_date': expire_date
            }
        )
        
        # Enviar boas-vindas apenas se for uma nova conta (tem senha temporária)
        if temp_password and phone:
            send_welcome_message(user, phone, email, temp_password)

    # 2. TRATAMENTO DE CANCELAMENTO OU ATRASO
    elif event_type in ['SUBSCRIPTION_CANCELLED', 'SUBSCRIPTION_OVERDUE', 'REFUND']:
        customer_data = payload.get('customer', {})
        email = customer_data.get('email')
        
        if email:
            user = User.objects.filter(email=email).first()
            if user and hasattr(user, 'subscription'):
                user.subscription.status = 'canceled'
                user.subscription.save()
                print(f"Acesso bloqueado para o usuário: {email}")

def send_welcome_message(user, phone, email, temp_password):
    evo = EvolutionService()
    msg = f"🚀 *Pagamento Confirmado!* \n\n"
    msg += f"Olá {user.nome}, seja muito bem-vindo(a) ao Agente Prime! \n\n"
    msg += "A partir de agora eu sou seu assistente pessoal. \n\n"
    msg += "Aqui estão seus dados de acesso ao painel web: \n"
    msg += f"🔗 Site: {settings.SITE_URL}\n"
    msg += f"📧 Email: {email}\n"
    msg += f"🔑 Senha: *{temp_password}* \n\n"
    msg += "Como posso te ajudar hoje?"
    evo.send_message(phone, msg)


@csrf_exempt
@require_http_methods(["POST"])
def evolution_webhook(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        event = payload.get('event')
        if event != 'messages.upsert': 
            return JsonResponse({'status': 'ignored'}, status=200)
            
        data = payload.get('data', {})
        # Evolution v2 às vezes envia data como uma lista
        if isinstance(data, list):
            data = data[0] if data else {}

        if data.get('key', {}).get('fromMe'): 
            return JsonResponse({'status': 'ignored_self'}, status=200)

        from_number = data.get('key', {}).get('remoteJid', '').split('@')[0]
        message_data = data.get('message', {})
        message_id = data.get('key', {}).get('id')

        # DEDUPLICAÇÃO: Evita processar a mesma mensagem duas vezes (causa do loop)
        from .models import WebhookEvent
        if WebhookEvent.objects.filter(event_id=message_id).exists():
            print(f"Mensagem {message_id} já processada. Ignorando duplicata.")
            return JsonResponse({'status': 'duplicate_ignored'}, status=200)

        # Registrar o evento para evitar processamento futuro desta mesma ID
        WebhookEvent.objects.create(
            source='whatsapp',
            event_id=message_id,
            event_type=event,
            payload=payload
        )

        user = User.objects.filter(telefone__icontains=from_number[-8:]).first()
        evo = EvolutionService()
        
        subscription = Subscription.objects.filter(user=user).first()
        from agents.services import AIAgentService
        agent = AIAgentService()
        
        body = message_data.get('conversation') or message_data.get('extendedTextMessage', {}).get('text', 'Olá')

        # Verifica se a assinatura está ativa (considerando status e data de expiração)
        if not subscription or not subscription.is_active:
            response_text = agent.process_inactive_user(body, user)
            
            from whatsapp_messages.models import Message
            Message.objects.create(
                user=user,
                phone_number=from_number,
                message_type='text',
                raw_content=body,
                response_sent=response_text,
                status='completed'
            )
            
            evo.send_message(from_number, response_text)
            return JsonResponse({'status': 'inactive_humanized'}, status=200)
        
        response_text = ""
        
        if 'imageMessage' in message_data:
            message_id = data.get('key', {}).get('id')
            base64_data = message_data.get('imageMessage', {}).get('base64')
            response_text = agent.process_image(message_id, user, base64_data=base64_data, message_obj=data)
        elif 'audioMessage' in message_data:
            message_id = data.get('key', {}).get('id')
            base64_data = message_data.get('audioMessage', {}).get('base64')
            response_text = agent.process_audio(message_id, user, base64_data=base64_data, message_obj=data)
        else:
            body = message_data.get('conversation') or message_data.get('extendedTextMessage', {}).get('text', '')
            if body:
                response_text = agent.process_message(body, user)
            else:
                return JsonResponse({'status': 'unsupported_type'}, status=200)
        
        if response_text:
            evo.send_message(from_number, response_text)
            
        return JsonResponse({'status': 'success'}, status=200)
    except Exception as e:
        print(f"Erro Evolution Webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def validate_kirvano_signature(signature, body):
    raw_secret = os.getenv('KIRVANO_WEBHOOK_SECRET') or os.getenv('KIRVANO_WEBHOOK_TOKEN')
    if not raw_secret:
        print("AVISO: Kirvano Webhook Secret não configurado no EasyPanel!")
        return True
    
    # Remove espaços em branco acidentais que podem vir do EasyPanel
    secret = raw_secret.strip()
    
    if not signature:
        return False
        
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(signature), str(expected))
