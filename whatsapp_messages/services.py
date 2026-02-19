import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EvolutionService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_BASE_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

    def send_presence(self, number, presence='composing'):
        """
        Envia o status de 'digitando...' ou 'gravando áudio...'
        """
        url = f"{self.base_url}/chat/presenceUpdate/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "number": ''.join(filter(str.isdigit, number)),
            "presence": presence # 'composing' = digitando, 'recording' = gravando
        }
        try:
            requests.post(url, json=payload, headers=headers)
        except:
            pass

    def send_message(self, number, text):
        """
        Envia mensagens de forma otimizada para evitar timeouts
        """
        import time
        if not all([self.base_url, self.api_key, self.instance]):
            logger.error("Configuração da Evolution API incompleta.")
            return False

        clean_number = ''.join(filter(str.isdigit, number))
        if len(clean_number) in [10, 11] and not clean_number.startswith('55'):
            clean_number = '55' + clean_number
        
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

        # 1. MOSTRAR 'DIGITANDO...' MAIS RÁPIDO
        self.send_presence(clean_number, 'composing')
        time.sleep(0.5)

        # 2. LIMPAR LITERAL \n\n
        text = text.replace('\\n', '\n')

        # 3. FRACIONAR APENAS SE FOR MUITO GRANDE (WHATSAPP LIMIT ~4096)
        max_chars = 4000
        if len(text) <= max_chars:
            parts = [text]
        else:
            parts = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

        success = True
        for part in parts:
            if not part.strip(): continue
            
            payload = {
                "number": clean_number,
                "text": part.strip()
            }
            try:
                print(f"Enviando bloco via Evolution ({len(part)} chars)...")
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                response.raise_for_status()
                print(f"Bloco enviado com sucesso!")
                if len(parts) > 1:
                    time.sleep(0.5)
            except Exception as e:
                print(f"ERRO EVOLUTION: {str(e)}")
                logger.error(f"Erro ao enviar parte da mensagem: {str(e)}")
                success = False
        
        return success
