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

from .models import WebhookEvent
from subscriptions.models import Subscription
from whatsapp_messages.models import Message
from whatsapp_messages.services import EvolutionService

User = get_user_model()


@csrf_exempt
@require_http_methods(["POST"])
def kirvano_webhook(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        signature = request.headers.get('X-Kirvano-Signature')
        if not validate_kirvano_signature(signature, request.body):
             return JsonResponse({'error': 'Invalid signature'}, status=401)
        event_id = payload.get('event_id') or payload.get('id')
        event_type = payload.get('event_type') or payload.get('type')
        if not event_id or not event_type:
            return JsonResponse({'error': 'Missing event_id or event_type'}, status=400)
        if WebhookEvent.is_duplicate(event_id):
            return JsonResponse({'status': 'already_processed'}, status=200)
        webhook_event = WebhookEvent.objects.create(source='kirvano', event_id=event_id, event_type=event_type, payload=payload, headers=dict(request.headers))
        try:
            process_kirvano_event(payload, event_type)
            webhook_event.mark_processed()
        except Exception as e:
            webhook_event.mark_error(str(e))
            return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse({'status': 'success'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def generate_random_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def process_kirvano_event(payload, event_type):
    if event_type == 'purchase.approved':
        customer_data = payload.get('customer', {})
        subscription_data = payload.get('subscription', {}) or payload.get('purchase', {})
        email = customer_data.get('email')
        phone = customer_data.get('phone')
        name = customer_data.get('name')
        if not email: raise ValueError('Email obrigatório')
        user = User.objects.filter(email=email).first()
        temp_password = None
        if not user:
            temp_password = generate_random_password()
            user = User.objects.create_user(email=email, telefone=phone or f"TEMP_{generate_random_password(4)}", nome=name or 'Cliente', password=temp_password)
            user.must_change_password = True
            user.save()
        Subscription.objects.update_or_create(user=user, defaults={'kirvano_subscription_id': subscription_data.get('id'), 'plan_name': subscription_data.get('plan_name', 'Plano Ativo'), 'status': 'active', 'start_date': timezone.now(), 'expire_date': subscription_data.get('expire_date')})
        if phone:
            evo = EvolutionService()
            msg = f"Olá {user.nome}! Sua assinatura aprovada! \n"
            if temp_password: msg += f" Email: {email}\n Senha: *{temp_password}*"
            evo.send_message(phone, msg)
    elif event_type in ['subscription.canceled', 'subscription.payment_failed']:
        Subscription.objects.filter(kirvano_subscription_id=payload.get('subscription', {}).get('id')).update(status='canceled')


@csrf_exempt
@require_http_methods(["POST"])
def evolution_webhook(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        event = payload.get('event')
        if event != 'messages.upsert': 
            return JsonResponse({'status': 'ignored'}, status=200)
            
        data = payload.get('data', {})
        if data.get('key', {}).get('fromMe'): 
            return JsonResponse({'status': 'ignored_self'}, status=200)

        from_number = data.get('key', {}).get('remoteJid', '').split('@')[0]
        message_data = data.get('message', {})
        
        user = User.objects.filter(telefone__icontains=from_number[-8:]).first()
        evo = EvolutionService()
        
        if not user:
            evo.send_message(from_number, "Assine o Agente.ai para usar estas funções: https://pay.kirvano.com/")
            return JsonResponse({'status': 'sent_checkout'}, status=200)
            
        subscription = Subscription.objects.filter(user=user).first()
        if not subscription or subscription.status != 'active':
            evo.send_message(from_number, "Assinatura inativa.")
            return JsonResponse({'status': 'inactive'}, status=200)

        from agents.services import AIAgentService
        agent = AIAgentService()
        
        # LÓGICA DE DETECÇÃO DE TIPO DE MENSAGEM
        response_text = ""
        
        # 1. IMAGEM
        if 'imageMessage' in message_data:
            file_url = f"{settings.EVOLUTION_BASE_URL}/chat/getMediaBinary/{settings.EVOLUTION_INSTANCE}/{data.get('key', {}).get('id')}"
            response_text = agent.process_image(file_url, user)
            
        # 2. ÁUDIO
        elif 'audioMessage' in message_data:
            file_url = f"{settings.EVOLUTION_BASE_URL}/chat/getMediaBinary/{settings.EVOLUTION_INSTANCE}/{data.get('key', {}).get('id')}"
            response_text = agent.process_audio(file_url, user)
            
        # 3. TEXTO
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
    secret = settings.KIRVANO_WEBHOOK_SECRET
    if not secret or not signature: return True
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
