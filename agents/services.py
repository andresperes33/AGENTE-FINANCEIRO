from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from transactions.models import Transaction
from agenda.models import Appointment
import json
import os
import re
import requests
import base64
import tempfile

# Tentar importar LangChain, se falhar usar Mock
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    from .prompts import ROUTER_PROMPT, TRANSACTION_PROMPT, REPORT_PROMPT, EDIT_PROMPT, VISION_PROMPT, SCHEDULE_PROMPT, INACTIVE_PROMPT
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    print("Aviso: LangChain não instalado. Usando Mock.")


class AIAgentService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if HAS_LANGCHAIN and self.api_key:
            try:
                self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=self.api_key, temperature=0)
            except Exception as e:
                print(f"Erro ao inicializar LLM: {e}")
                self.llm = None
        else:
            self.llm = None
    
    def process_message(self, text, user):
        """Processa a mensagem do usuário e retorna uma resposta."""
        intent = self._route_intent(text)
        
        if intent == "TRANSACTION":
            return self._handle_transaction(text, user)
        elif intent == "REPORT":
            return self._handle_report(text, user)
        elif intent == "EDIT":
            return self._handle_edit(text, user)
        elif intent == "DELETE":
            return self._handle_delete(text, user)
        elif intent == "SCHEDULE":
            return self._handle_schedule(text, user)
        else:
            return "Desculpe, não entendi. Tente algo como 'Gastei 50 no almoço' ou mande um áudio/foto!"

    def process_inactive_user(self, text):
        """Gera uma resposta humanizada para usuários sem assinatura ativa"""
        if not self.llm:
            return "Adoraria te ajudar, mas as funções avançadas são para assinantes. Ative agora em: https://pay.kirvano.com/"
        
        try:
            prompt = PromptTemplate.from_template(INACTIVE_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"text": text})
            return response.content
        except:
            return "Adoraria te ajudar, mas as funções avançadas são para assinantes. Ative agora em: https://pay.kirvano.com/"

    def process_image(self, image_url, user):
        """Analisa imagem de comprovante usando Vision do GPT-4o-mini"""
        if not self.llm or not self.api_key:
            return "A inteligência visual precisa de uma chave OpenAI ativa."

        try:
            response = requests.get(image_url)
            if response.status_code != 200:
                return "Não consegui baixar a imagem para analisar."
            
            base64_image = base64.b64encode(response.content).decode('utf-8')

            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": [{"type": "text", "text": VISION_PROMPT}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                "max_tokens": 500
            }

            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            result = res.json()
            content = result['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            if "error" in data: return f"Não consegui ler o comprovante: {data['error']}"

            amount = float(str(data.get('amount', 0)).replace(',', '.'))
            tx = Transaction.objects.create(user=user, description=data.get('description', 'Comprovante'), amount=amount, type=data.get('type', 'expense'), category=data.get('category', 'Outros'), transaction_date=timezone.now().date())
            return f" *Comprovante Lido!* \n {tx.description}\n Valor: *R$ {amount:.2f}*\n ID: *{tx.identifier}*"
        except Exception as e: return f"Erro ao analisar o comprovante: {str(e)}"

    def process_audio(self, audio_url, user):
        """Transcreve áudio com Whisper e processa o texto"""
        if not self.api_key:
            return "A transcrição de áudio precisa de uma chave OpenAI ativa."

        try:
            # 1. Baixar o arquivo de áudio da Evolution
            response = requests.get(audio_url)
            if response.status_code != 200:
                return "Não consegui baixar o áudio para transcrever."

            # 2. Criar arquivo temporário para enviar para a OpenAI
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                temp_audio.write(response.content)
                temp_path = temp_audio.name

            # 3. Chamar Whisper API
            headers = {"Authorization": f"Bearer {self.api_key}"}
            files = {"file": open(temp_path, "rb")}
            data = {"model": "whisper-1", "language": "pt"}

            res = requests.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
            os.remove(temp_path) # Limpar temporário
            
            if res.status_code != 200:
                return "Erro ao transcrever o áudio com Whisper."
            
            transcription = res.json().get("text", "")
            if not transcription:
                return "O áudio parece estar vazio ou não foi compreendido."

            # 4. Processar o texto transcrito como se fosse uma mensagem normal
            response_text = self.process_message(transcription, user)
            return f" *Transcrição:* \"{transcription}\"\n\n{response_text}"

        except Exception as e:
            return f"Erro ao processar áudio: {str(e)}"

    def _route_intent(self, text):
        if not self.llm:
            lower_text = text.lower()
            if any(x in lower_text for x in ['gastei', 'comprei', 'paguei', 'recebi', 'ganhei', 'salário']): return "TRANSACTION"
            if any(x in lower_text for x in ['quanto', 'total', 'saldo', 'relatório', 'resumo']): return "REPORT"
            if any(x in lower_text for x in ['muda', 'altera', 'corrige', 'edita']): return "EDIT"
            if any(x in lower_text for x in ['apaga', 'deleta', 'exclui', 'remove']): return "DELETE"
            if any(x in lower_text for x in ['anota', 'agenda', 'lembrete', 'reunião']): return "SCHEDULE"
            return "OTHER"
        try:
            prompt = PromptTemplate.from_template(ROUTER_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"text": text})
            return response.content.strip().upper()
        except: return "OTHER"

    def _handle_transaction(self, text, user):
        try:
            parser = JsonOutputParser()
            prompt = PromptTemplate(template=TRANSACTION_PROMPT, input_variables=["text"], partial_variables={"format_instructions": parser.get_format_instructions()})
            chain = prompt | self.llm | parser
            data = chain.invoke({"text": text})
            amount = float(str(data.get('amount', 0)).replace(',', '.'))
            tx = Transaction.objects.create(user=user, description=data.get('description', 'Transação'), amount=amount, type=data.get('type', 'expense'), category=data.get('category', 'Outros'), transaction_date=timezone.now().date())
            return f" Lançamento Realizado! ID: *{tx.identifier}* - R$ {amount:.2f}"
        except: return "Erro ao processar lançamento."

    def _handle_edit(self, text, user):
        try:
            parser = JsonOutputParser()
            prompt = PromptTemplate(template=EDIT_PROMPT, input_variables=["text"], partial_variables={"format_instructions": parser.get_format_instructions()})
            chain = prompt | self.llm | parser
            data = chain.invoke({"text": text})
            identifier = data.get('identifier', '').upper()
            tx = Transaction.objects.filter(user=user, identifier=identifier).first()
            if not tx: return f"ID {identifier} não encontrado."
            if data.get('description'): tx.description = data['description']
            if data.get('amount'): tx.amount = float(str(data['amount']).replace(',', '.'))
            if data.get('category'): tx.category = data['category']
            tx.save()
            return f" Transação {identifier} atualizada!"
        except Exception as e: return f"Erro: {str(e)}"

    def _handle_delete(self, text, user):
        match = re.search(r'\b([A-Z0-9]{4})\b', text.upper())
        if not match: return "Informe o ID de 4 caracteres."
        tx = Transaction.objects.filter(user=user, identifier=match.group(1)).first()
        if not tx: return "ID não encontrado."
        id_code = tx.identifier
        tx.delete()
        return f" Transação *{id_code}* excluída!"

    def _handle_report(self, text, user):
        today = timezone.now().date()
        txs = Transaction.objects.filter(user=user, transaction_date__month=today.month).order_by('-transaction_date')[:5]
        total_income = sum(t.amount for t in Transaction.objects.filter(user=user, type='income', transaction_date__month=today.month))
        total_expense = sum(t.amount for t in Transaction.objects.filter(user=user, type='expense', transaction_date__month=today.month))
        tx_list = "\n".join([f"- *{t.identifier}*: {t.description} (R$ {t.amount:.2f})" for t in txs])
        context = f"Saldo: R$ {total_income - total_expense:.2f}\nÚltimas:\n{tx_list}"
        if not self.llm: return f" Resumo:\n{context}"
        try:
            prompt = PromptTemplate.from_template(REPORT_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"context": context, "question": text})
            return response.content
        except: return context

    def _handle_schedule(self, text, user):
        try:
            parser = JsonOutputParser()
            today = timezone.now()
            today_str = today.strftime('%Y-%m-%d')
            tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            
            prompt = PromptTemplate(
                template=SCHEDULE_PROMPT, 
                input_variables=["text"], 
                partial_variables={
                    "format_instructions": parser.get_format_instructions(),
                    "today": today_str,
                    "today_plus_1": tomorrow_str
                }
            )
            chain = prompt | self.llm | parser
            data = chain.invoke({"text": text})
            
            # Combinar data e hora
            dt_str = f"{data.get('date')} {data.get('time')}"
            dt_obj = timezone.make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M'))
            
            appt = Appointment.objects.create(
                user=user,
                title=data.get('title', 'Compromisso'),
                date_time=dt_obj
            )
            return f" ✅ *Compromisso Agendado!* \n📌 {appt.title}\n📅 {dt_obj.strftime('%d/%m/%Y às %H:%M')}\nID: *{appt.identifier}*"
        except Exception as e:
            return f"Erro ao agendar: {str(e)}"
