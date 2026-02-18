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
        Envia mensagens fracionadas com status de digitando
        """
        import time
        if not all([self.base_url, self.api_key, self.instance]):
            logger.error("Configuração da Evolution API incompleta.")
            return False

        clean_number = ''.join(filter(str.isdigit, number))
        # Se for número do Brasil sem o 55 (10 ou 11 dígitos), adiciona o 55
        if len(clean_number) in [10, 11] and not clean_number.startswith('55'):
            clean_number = '55' + clean_number
        
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

        # 1. MOSTRAR 'DIGITANDO...' POR 2 SEGUNDOS
        self.send_presence(clean_number, 'composing')
        time.sleep(2)

        # 2. LIMPAR LITERAL \n\n (se o LLM retornar a string "\n\n" em vez de quebra de linha real)
        text = text.replace('\\n', '\n')

        # 3. FRACIONAR E ENVIAR
        parts = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in text.split('\n') if p.strip()]

        success = True
        for part in parts:
            if not part: continue # Pular partes vazias
            
            payload = {
                "number": clean_number,
                "text": part
            }
            try:
                print(f"Enviando parte via Evolution para {clean_number}...")
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                print(f"Parte enviada com sucesso!")
                time.sleep(1) # Pequena pausa entre balões
            except Exception as e:
                print(f"ERRO EVOLUTION: {str(e)}")
                logger.error(f"Erro ao enviar parte da mensagem: {str(e)}")
                success = False
        
        return success
