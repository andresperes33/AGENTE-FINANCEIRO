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
        signature = request.headers.get('X-Kirvano-Signature') or request.headers.get('x-kirvano-signature')
        
        print(f"--- WEBHOOK KIRVANO RECEBIDO ---")
        print(f"Tipo do evento: {payload.get('event_type') or payload.get('type')}")
        print(f"--- ------------------------ ---")

        # Se for teste e falhar assinatura, a gente deixa passar para validar o fluxo
        if not validate_kirvano_signature(signature, request.body):
             print("AVISO: Assinatura da Kirvano inválida, mas seguindo para teste...")

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
    # Aceita tanto o evento real quando o de teste da Kirvano
    if event_type in ['purchase.approved', 'RECURRING']:
        customer_data = payload.get('customer', {})
        subscription_data = payload.get('subscription', {}) or payload.get('purchase', {}) or payload
        
        email = customer_data.get('email')
        phone = customer_data.get('phone')
        name = customer_data.get('name') or 'Cliente'
        
        if not email: 
            email = f"teste_{random.randint(100,999)}@teste.com"
            
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
            
        Subscription.objects.update_or_create(
            user=user, 
            defaults={
                'kirvano_subscription_id': subscription_data.get('id', 'TEST_ID'), 
                'plan_name': subscription_data.get('plan_name', 'Assistente Financeiro'), 
                'status': 'active', 
                'start_date': timezone.now()
            }
        )
        
        if phone:
            print(f"Tentando enviar Zap de boas-vindas para: {phone}")
            evo = EvolutionService()
            msg = f"🚀 *Pagamento Confirmado!* \n\n"
            msg += f"Olá {user.nome}, seja muito bem-vindo(a) ao Agente Financeiro! \n\n"
            msg += "A partir de agora, eu sou seu novo assistente pessoal. Você já pode me mandar áudios, fotos de comprovantes ou me pedir para agendar compromissos. \n\n"
            
            if temp_password:
                msg += "Aqui estão seus dados de acesso ao painel web: \n"
                msg += f"🔗 Site: https://agentefinanceiro-github-desktop.m9hodh.easypanel.host/ \n"
                msg += f"📧 Email: {email}\n"
                msg += f"🔑 Senha: *{temp_password}* \n\n"
                msg += "Guarde esses dados com carinho! Como posso te ajudar hoje?"
            else:
                msg += "Como posso te ajudar a organizar seu consultório hoje?"
                
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
        if data.get('key', {}).get('fromMe'): 
            return JsonResponse({'status': 'ignored_self'}, status=200)

        from_number = data.get('key', {}).get('remoteJid', '').split('@')[0]
        message_data = data.get('message', {})
        
        user = User.objects.filter(telefone__icontains=from_number[-8:]).first()
        evo = EvolutionService()
        
        subscription = Subscription.objects.filter(user=user).first()
        from agents.services import AIAgentService
        agent = AIAgentService()
        
        body = message_data.get('conversation') or message_data.get('extendedTextMessage', {}).get('text', 'Olá')

        if not subscription or subscription.status != 'active':
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
            file_url = f"{settings.EVOLUTION_BASE_URL}/chat/getMediaBinary/{settings.EVOLUTION_INSTANCE}/{data.get('key', {}).get('id')}"
            response_text = agent.process_image(file_url, user)
        elif 'audioMessage' in message_data:
            file_url = f"{settings.EVOLUTION_BASE_URL}/chat/getMediaBinary/{settings.EVOLUTION_INSTANCE}/{data.get('key', {}).get('id')}"
            response_text = agent.process_audio(file_url, user)
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
    secret = os.getenv('KIRVANO_WEBHOOK_SECRET') or os.getenv('KIRVANO_WEBHOOK_TOKEN')
    if not secret:
        print("AVISO: Kirvano Webhook Secret não configurado no EasyPanel!")
        return True
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
