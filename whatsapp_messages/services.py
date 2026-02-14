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
        Envia uma mensagem de texto via Evolution API
        """
        if not all([self.base_url, self.api_key, self.instance]):
            logger.error("Configuração da Evolution API incompleta.")
            return False

        # Formatar número (garantir que termina com @s.whatsapp.net se necessário)
        # O Evolution aceita o número limpo ou formatado.
        # Vamos garantir o formato esperado pela API.
        clean_number = ''.join(filter(str.isdigit, number))
        
        url = f"{self.base_url}/message/sendText/{self.instance}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": clean_number,
            "text": text
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem via Evolution: {str(e)}")
            return False
