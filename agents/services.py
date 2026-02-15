from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone
from transactions.models import Transaction
from agenda.models import Appointment
from whatsapp_messages.models import Message
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
    from .prompts import ROUTER_PROMPT, TRANSACTION_PROMPT, REPORT_PROMPT, EDIT_PROMPT, VISION_PROMPT, SCHEDULE_PROMPT, INACTIVE_PROMPT, ACTIVE_GENERAL_PROMPT, DELETE_PROMPT, REPORT_PARAMS_PROMPT
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
            return self._handle_general_chat(text, user)

    def gen_notification_text(self, prompt_text):
        """Gera apenas o texto da notificação sem processar intenções"""
        if not self.llm:
            return prompt_text
        try:
            response = self.llm.invoke(prompt_text)
            return response.content
        except:
            return prompt_text

    def process_inactive_user(self, text, user):
        """Gera uma resposta humanizada e com memória para usuários sem assinatura ativa"""
        if not self.llm:
            return "Adoraria te ajudar, mas as funções avançadas são para assinantes. Ative agora em: https://pay.kirvano.com/6202e7eb-b115-412d-aa32-5fb797c45c0b"
        
        try:
            # Buscar histórico das últimas 5 mensagens
            history_msgs = Message.objects.filter(user=user).order_by('-created_at')[:5]
            history_text = ""
            for msg in reversed(history_msgs):
                history_text += f"Usuário: {msg.raw_content}\nAgente: {msg.response_sent}\n"

            prompt = PromptTemplate.from_template(INACTIVE_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"text": text, "history": history_text or "Início da conversa."})
            return response.content
        except Exception as e:
            print(f"Erro Memória: {e}")
            return "Adoraria te ajudar, mas as funções avançadas são para assinantes. Ative agora em: https://pay.kirvano.com/6202e7eb-b115-412d-aa32-5fb797c45c0b"

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
            
            response = f"✅ *Novo Lançamento Realizado! (via Foto)* \n\n"
            response += f"🆔 *ID:* {tx.identifier}\n"
            response += f"💰 *Valor:* R$ {amount:.2f}\n"
            response += f"🏷️ *Tipo:* {'Receita' if tx.type == 'income' else 'Despesa'}\n"
            response += f"📄 *Descrição:* {tx.description}\n"
            response += f"🏷️ *Categoria:* {tx.category}\n"
            response += f"📅 *Data:* {tx.transaction_date.strftime('%d/%m/%Y')}\n\n"
            response += f"❌ Para excluir ou editar, envie o ID: *{tx.identifier}*"
            return response
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
            if any(x in lower_text for x in ['quanto', 'total', 'saldo', 'relatório', 'resumo', 'mês', 'hoje', 'ontem']): return "REPORT"
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
            
            response = f"✅ *Novo Lançamento Realizado!* \n\n"
            response += f"🆔 *ID:* {tx.identifier}\n"
            response += f"💰 *Valor:* R$ {amount:.2f}\n"
            response += f"🏷️ *Tipo:* {'Receita' if tx.type == 'income' else 'Despesa'}\n"
            response += f"📄 *Descrição:* {tx.description}\n"
            response += f"🏷️ *Categoria:* {tx.category}\n"
            response += f"📅 *Data:* {tx.transaction_date.strftime('%d/%m/%Y')}\n\n"
            response += f"❌ Para excluir ou editar, envie o ID: *{tx.identifier}*"
            return response
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
            
            response = f"🔄 *Lançamento Atualizado com Sucesso!* \n\n"
            response += f"🆔 *ID:* {tx.identifier}\n"
            response += f"💰 *Valor:* R$ {tx.amount:.2f}\n"
            response += f"🏷️ *Tipo:* {'Receita' if tx.type == 'income' else 'Despesa'}\n"
            response += f"📄 *Descrição:* {tx.description}\n"
            response += f"🏷️ *Categoria:* {tx.category}\n"
            response += f"📅 *Data:* {tx.transaction_date.strftime('%d/%m/%Y')}\n\n"
            response += f"✅ Todas as alterações foram salvas no seu painel."
            return response
        except Exception as e: return f"Erro: {str(e)}"

    def _handle_delete(self, text, user):
        try:
            if not self.llm:
                # Fallback para regex se o LLM não estiver disponível
                match = re.search(r'\b([A-Z0-9]{4})\b', text.upper())
                if not match: return "Informe o ID de 4 caracteres."
                identifier = match.group(1)
            else:
                parser = JsonOutputParser()
                prompt = PromptTemplate(
                    template=DELETE_PROMPT, 
                    input_variables=["text"], 
                    partial_variables={"format_instructions": parser.get_format_instructions()}
                )
                chain = prompt | self.llm | parser
                data = chain.invoke({"text": text})
                identifier = data.get('identifier', '').upper()

            if not identifier:
                return "Não consegui identificar o ID na sua mensagem. Por favor, envie o ID de 4 caracteres (Ex: 6N5G)."

            tx = Transaction.objects.filter(user=user, identifier=identifier).first()
            if not tx: return f"ID *{identifier}* não encontrado."
            
            id_code = tx.identifier
            description = tx.description
            tx.delete()
            return f"✅ Transação *{id_code}* ({description}) excluída com sucesso!"
        except Exception as e:
            return f"Erro ao excluir: {str(e)}"

    def _handle_report(self, text, user):
        today = timezone.now().date()
        
        # 1. Tentar extrair parâmetros da pergunta (Data e Categoria)
        params = {"start_date": None, "end_date": None, "category": None, "is_detailed": False}
        if self.llm:
            try:
                parser = JsonOutputParser()
                prompt = PromptTemplate(
                    template=REPORT_PARAMS_PROMPT, 
                    input_variables=["text"], 
                    partial_variables={"today": today.strftime('%d/%m/%Y'), "format_instructions": parser.get_format_instructions()}
                )
                chain = prompt | self.llm | parser
                params = chain.invoke({"text": text})
            except Exception as e:
                print(f"Erro ao extrair parâmetros do relatório: {e}")

        # 2. Definir Período (Padrão: Mês Atual se não especificado)
        start_date_str = params.get('start_date')
        end_date_str = params.get('end_date')
        category_filter = params.get('category')
        
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date = today.replace(day=1)
        except:
            start_date = today.replace(day=1)
            
        try:
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                end_date = today
        except:
            end_date = today

        # 3. Filtrar Transações
        query = Transaction.objects.filter(user=user, transaction_date__range=[start_date, end_date])
        
        # Se houver filtro de categoria (especificado pelo usuário)
        if category_filter:
            # Tentar busca flexível pela categoria
            query = query.filter(category__icontains=category_filter)

        transactions = query.order_by('transaction_date')
        
        # 4. Construir Contexto
        income_txs = transactions.filter(type='income')
        expense_txs = transactions.filter(type='expense')
        
        total_income = sum(t.amount for t in income_txs)
        total_expense = sum(t.amount for t in expense_txs)
        
        # Lista de itens (Sempre incluímos se houver filtro de categoria ou for detalhado)
        items_list = "\n".join([
            f"📍 ID: {t.identifier} | DATA: {t.transaction_date.strftime('%d/%m')} | ITEM: {t.description} | VALOR: R$ {t.amount:.2f} | CATEGORIA: {t.category} | TIPO: {'Receita' if t.type == 'income' else 'Despesa'}" 
            for t in transactions
        ])

        context = f"PERÍODO: {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}\n"
        if category_filter:
            context += f"FILTRO DE CATEGORIA: {category_filter}\n"
        context += f"\n--- LISTA DE MOVIMENTAÇÕES ---\n"
        context += f"{items_list if items_list else 'NENHUMA MOVIMENTAÇÃO ENCONTRADA NO PERÍODO.'}\n\n"
        context += f"--- RESUMO ---\n"
        context += f"TOTAL GANHOS: R$ {total_income:.2f}\n"
        context += f"TOTAL GASTOS: R$ {total_expense:.2f}\n"
        context += f"SALDO DO PERÍODO: R$ {total_income - total_expense:.2f}"

        if not self.llm: 
            return f"📊 *Relatório Financeiro* \n\n{context}"
            
        try:
            prompt = PromptTemplate.from_template(REPORT_PROMPT)
            chain = prompt | self.llm
            # Passamos a pergunta original e o contexto filtrado
            response = chain.invoke({"context": context, "question": text})
            return response.content
        except: 
            return f"📊 *Relatório Financeiro* \n\n{context}"

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
    def _handle_general_chat(self, text, user):
        """Lida com conversas gerais (oi, tudo bem, etc) para usuários ativos"""
        if not self.llm:
            return "Oi! Como posso te ajudar hoje? Posso anotar seus gastos, agendar compromissos ou gerar relatórios. É só me chamar!"
            
        try:
            # Buscar histórico das últimas 5 mensagens
            history_msgs = Message.objects.filter(user=user).order_by('-created_at')[:5]
            history_text = ""
            for msg in reversed(history_msgs):
                history_text += f"Usuário: {msg.raw_content}\nAgente: {msg.response_sent}\n"

            prompt = PromptTemplate.from_template(ACTIVE_GENERAL_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"text": text, "history": history_text or "Início da conversa."})
            return response.content
        except Exception as e:
            print(f"Erro Chat Geral: {e}")
            return "Oi! Estou pronto para te ajudar. Quer anotar um gasto, ver seu saldo ou agendar algo?"
