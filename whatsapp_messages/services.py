import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EvolutionService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_BASE_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

    def send_message(self, number, text):
        """
        Envia mensagens fracionadas para parecer humano
        """
        import time
        if not all([self.base_url, self.api_key, self.instance]):
            logger.error("Configuração da Evolution API incompleta.")
            return False

        clean_number = ''.join(filter(str.isdigit, number))
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

        # Divide o texto em blocos baseados em parágrafos (linha dupla)
        # Se não houver linha dupla, tenta por linha simples, mas filtra vazios
        parts = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in text.split('\n') if p.strip()]

        success = True
        for part in parts:
            payload = {
                "number": clean_number,
                "text": part
            }
            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                # Pequena pausa entre mensagens para simular digitação
                time.sleep(1.5)
            except Exception as e:
                logger.error(f"Erro ao enviar parte da mensagem: {str(e)}")
                success = False
        
        return success
