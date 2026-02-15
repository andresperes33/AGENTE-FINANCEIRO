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

    def process_image(self, message_id, user, base64_data=None, message_obj=None):
        """Analisa imagem de comprovante usando Vision do GPT-4o-mini"""
        if not self.llm or not self.api_key:
            return "A inteligência visual precisa de uma chave OpenAI ativa."

        try:
            # 1. Obter binário da imagem
            if base64_data:
                base64_image = base64_data
            else:
                # Tentar baixar via Evolution API (várias tentativas/endpoints)
                media_bytes = self._get_evolution_media(message_id, message_obj)
                if not media_bytes:
                    return "Não consegui baixar a imagem para analisar. Verifique se a Evolution API está configurada corretamente."
                
                base64_image = base64.b64encode(media_bytes).decode('utf-8')

            # 2. Chamar OpenAI Vision
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": VISION_PROMPT}, 
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                "max_tokens": 500
            }

            headers_oa = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_oa, json=payload)
            result = res.json()
            content = result['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            if "error" in data: return f"Não consegui ler o comprovante: {data['error']}"

            amount = float(str(data.get('amount', 0)).replace(',', '.'))
            tx = Transaction.objects.create(user=user, description=data.get('description', 'Comprovante'), amount=amount, type=data.get('type', 'expense'), category=data.get('category', 'Outros'), transaction_date=timezone.now().date())
            
            response = f"✨ *LANÇAMENTO VIA FOTO CONCLUÍDO!* ✨\n\n"
            response += f"🆔 **Identificador:** `{tx.identifier}`\n"
            response += f"💰 **Valor:** `R$ {amount:.2f}`\n"
            response += f"📂 **Categoria:** {tx.category}\n"
            response += f"📝 **Descrição:** {tx.description}\n"
            response += f"🕒 **Data:** {tx.transaction_date.strftime('%d/%m/%Y')}\n"
            response += f"📊 **Tipo:** {'📈 Receita' if tx.type == 'income' else '📉 Despesa'}\n\n"
            response += f"💡 _Dica: Você pode editar ou excluir este lançamento usando o ID_ `{tx.identifier}`."
            return response
        except Exception as e: return f"Erro ao analisar o comprovante: {str(e)}"

    def process_audio(self, message_id, user, base64_data=None, message_obj=None):
        """Transcreve áudio com Whisper e processa o texto"""
        if not self.api_key:
            return "A transcrição de áudio precisa de uma chave OpenAI ativa."

        try:
            # 1. Obter binário do áudio
            if base64_data:
                audio_data = base64.b64decode(base64_data)
            else:
                audio_data = self._get_evolution_media(message_id, message_obj)
                
                if not audio_data:
                    return "Não consegui baixar o áudio para transcrever. Verifique se a Evolution API está configurada corretamente."

            # 2. Criar arquivo temporário para enviar para a OpenAI
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                temp_audio.write(audio_data)
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
            print(f"🎤 [DEBUG] Transcrição do Áudio: '{transcription}'") # LOG PARA DEBUG

            if not transcription or len(transcription.strip()) < 2:
                return "O áudio parece estar mudo ou muito curto. Tente novamente."

            # 4. Processar o texto transcrito como se fosse uma mensagem normal
            response_text = self.process_message(transcription, user)
            return response_text

        except Exception as e:
            return f"Erro ao processar áudio: {str(e)}"

    def _get_evolution_media(self, message_id, message_obj=None):
        """Tenta baixar a mídia por diversos endpoints da Evolution API (v1 e v2)"""
        headers = {"apikey": settings.EVOLUTION_API_KEY}
        instance = settings.EVOLUTION_INSTANCE
        base_url = settings.EVOLUTION_BASE_URL

        # 1. Tentar POST /chat/getBase64FromMediaMessage/{instance} (Recomendado para Evolution v2)
        try:
            url_base64 = f"{base_url}/chat/getBase64FromMediaMessage/{instance}"
            # O endpoint v2 geralmente espera o objeto de mensagem completo ou o messageId
            if message_obj:
                # Payload sugerido para v2 quando se tem o objeto do webhook
                payload = {"message": message_obj}
            else:
                payload = {"messageId": message_id}
                
            res = requests.post(url_base64, headers=headers, json=payload, timeout=10)
            if res.status_code in [200, 201]:
                data = res.json()
                # A resposta pode vir em diferentes formatos dependendo da versão
                base64_str = None
                if isinstance(data, dict):
                    base64_str = data.get('base64') or data.get('response', {}).get('base64')
                
                if base64_str:
                    # Remover cabeçalho data:image/...;base64, se houver
                    if ',' in base64_str:
                        base64_str = base64_str.split(',')[1]
                    return base64.b64decode(base64_str)
        except Exception as e:
            print(f"Erro no endpoint getBase64: {e}")

        # 2. Tentar GET /chat/fetchMediaBinary/{instance}/{messageId} (Padrão v2)
        try:
            url_fetch = f"{base_url}/chat/fetchMediaBinary/{instance}/{message_id}"
            res = requests.get(url_fetch, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.content
        except: pass

        # 3. Tentar GET /chat/getMediaBinary/{instance}/{messageId} (Padrão v1)
        try:
            url_get = f"{base_url}/chat/getMediaBinary/{instance}/{message_id}"
            res = requests.get(url_get, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.content
        except: pass

        print(f"Falha total ao baixar mídia {message_id} após várias tentativas.")
        return None

    def _route_intent(self, text):
        lower_text = text.lower()
        
        # Fallback ou Pré-processamento: Priorizar REPORT se houver termos de consulta
        # mesmo que tenha termos de transação (ex: "quanto gastei")
        query_terms = ['quanto', 'o que', 'total', 'saldo', 'relatório', 'resumo', 'lista', 'mostra', 'balanço', 'nesse mês', 'neste mês', 'nessa semana', 'nesta semana', 'hoje', 'ontem']
        transaction_terms = ['gastei', 'comprei', 'paguei', 'recebi', 'ganhei', 'salário', 'pix']
        
        has_query = any(x in lower_text for x in query_terms)
        has_transaction = any(x in lower_text for x in transaction_terms)
        
        if not self.llm:
            if has_query: return "REPORT"
            if has_transaction: return "TRANSACTION"
            if any(x in lower_text for x in ['muda', 'altera', 'corrige', 'edita']): return "EDIT"
            if any(x in lower_text for x in ['apaga', 'deleta', 'exclui', 'remove']): return "DELETE"
            if any(x in lower_text for x in ['anota', 'agenda', 'lembrete', 'reunião']): return "SCHEDULE"
            return "OTHER"
            
        try:
            # Se a mensagem tiver termos de consulta e transação (ex: "Quanto gastei..."), 
            # o LLM às vezes se confunde. Vamos reforçar a intenção.
            prompt = PromptTemplate.from_template(ROUTER_PROMPT)
            chain = prompt | self.llm
            response = chain.invoke({"text": text})
            intent = response.content.strip().upper()
            
            # Reforço de segurança: se o LLM disse TRANSACTION mas tem termos de query claros, 
            # e o valor extraído depois for 0, o ideal seria REPORT.
            # Mas vamos confiar na atualização do prompt por enquanto.
            return intent
        except: return "OTHER"

    def _handle_transaction(self, text, user):
        try:
            parser = JsonOutputParser()
            prompt = PromptTemplate(template=TRANSACTION_PROMPT, input_variables=["text"], partial_variables={"format_instructions": parser.get_format_instructions()})
            chain = prompt | self.llm | parser
            data = chain.invoke({"text": text})
            amount = float(str(data.get('amount', 0)).replace(',', '.'))
            tx = Transaction.objects.create(user=user, description=data.get('description', 'Transação'), amount=amount, type=data.get('type', 'expense'), category=data.get('category', 'Outros'), transaction_date=timezone.now().date())
            
            response = f"✅ **LANÇAMENTO REGISTRADO!**\n\n"
            response += f"🆔 **ID:** `{tx.identifier}`\n"
            response += f"💰 **Valor:** `R$ {amount:.2f}`\n"
            response += f"📂 **Categoria:** {tx.category}\n"
            response += f"📝 **Descrição:** {tx.description}\n"
            response += f"🕒 **Data:** {tx.transaction_date.strftime('%d/%m/%Y')}\n"
            response += f"📊 **Tipo:** {'📈 Receita' if tx.type == 'income' else '📉 Despesa'}\n\n"
            response += f"🗑️ _Para remover, envie: \"apaga {tx.identifier}\"_"
            return response
        except: return "Erro ao processar lançamento."

    def _handle_edit(self, text, user):
        try:
            today = timezone.now().date().strftime('%Y-%m-%d')
            parser = JsonOutputParser()
            prompt = PromptTemplate(
                template=EDIT_PROMPT, 
                input_variables=["text"], 
                partial_variables={
                    "format_instructions": parser.get_format_instructions(),
                    "today": today
                }
            )
            chain = prompt | self.llm | parser
            data = chain.invoke({"text": text})
            
            identifier = data.get('identifier', '').upper()
            if not identifier:
                return "Não consegui identificar o ID do registro que você quer editar."

            # Verificar se é compromisso ou transação pelo prefixo do ID
            if identifier.startswith('AG'):
                # EDITAR COMPROMISSO
                appt = Appointment.objects.filter(user=user, identifier=identifier).first()
                if not appt: return f"❌ Compromisso ID `{identifier}` não encontrado."

                changed = False
                if data.get('title') or data.get('description'):
                    appt.title = data.get('title') or data.get('description')
                    changed = True
                
                # Se mudou data ou hora, precisamos recompor o date_time
                new_date = data.get('date')
                new_time = data.get('time')

                if new_date or new_time:
                    current_dt = appt.date_time
                    d = datetime.strptime(new_date, '%Y-%m-%d').date() if new_date else current_dt.date()
                    t = datetime.strptime(new_time, '%H:%M').time() if new_time else current_dt.time()
                    appt.date_time = timezone.make_aware(datetime.combine(d, t))
                    changed = True

                if changed:
                    appt.save()
                    return f"🔄 **AGENDAMENTO ATUALIZADO!**\n\n📌 **O quê:** {appt.title}\n🕒 **Quando:** {appt.date_time.strftime('%d/%m/%Y às %H:%M')}\n🆔 **ID:** `{appt.identifier}`"
                else:
                    return "Não identifiquei alterações para fazer no compromisso."

            else:
                # EDITAR TRANSAÇÃO
                tx = Transaction.objects.filter(user=user, identifier=identifier).first()
                if not tx: 
                    return f"❌ ID `{identifier}` não encontrado em seus registros."

                # Atualizar campos apenas se foram fornecidos
                if data.get('description') is not None:
                    tx.description = data['description']
                
                if data.get('amount') is not None:
                    tx.amount = float(str(data['amount']).replace(',', '.'))
                
                if data.get('category') is not None:
                    tx.category = data['category']
                    
                if data.get('type') is not None:
                    tx.type = data['type']
                    
                if data.get('date') is not None:
                    tx.transaction_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

                tx.save()
                
                response = f"🔄 **LANÇAMENTO ATUALIZADO!**\n\n"
                response += f"🆔 **ID:** `{tx.identifier}`\n"
                response += f"💰 **Valor:** `R$ {tx.amount:.2f}`\n"
                response += f"📂 **Categoria:** {tx.category}\n"
                response += f"📝 **Descrição:** {tx.description}\n"
                response += f"🕒 **Data:** {tx.transaction_date.strftime('%d/%m/%Y')}\n"
                response += f"📊 **Tipo:** {'📈 Receita' if tx.type == 'income' else '📉 Despesa'}\n\n"
                response += f"✨ _As alterações já estão refletidas no seu painel._"
                return response
        except Exception as e: 
            return f"⚠️ Erro ao editar registro: {str(e)}"

    def _handle_delete(self, text, user):
        try:
            if not self.llm:
                # Fallback para regex
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
                return "Não consegui identificar o ID na sua mensagem. Por favor, envie o ID de 4 caracteres (Ex: 6N5G ou AG3D)."

            if identifier.startswith('AG'):
                # EXCLUIR COMPROMISSO
                appt = Appointment.objects.filter(user=user, identifier=identifier).first()
                if not appt: return f"ID *{identifier}* não encontrado na sua agenda."
                title = appt.title
                appt.delete()
                return f"🗑️ **COMPROMISSO REMOVIDO!**\n\n✅ O evento `{identifier}` (*{title}*) foi excluído da sua agenda."
            else:
                # EXCLUIR TRANSAÇÃO
                tx = Transaction.objects.filter(user=user, identifier=identifier).first()
                if not tx: return f"ID *{identifier}* não encontrado em suas finanças."
                id_code = tx.identifier
                description = tx.description
                tx.delete()
                return f"🗑️ **LANÇAMENTO EXCLUÍDO!**\n\n✅ A transação `{id_code}` (*{description}*) foi removida com sucesso."
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
        
        # 4. Construir Contexto (Otimizado para o Prompt Premium)
        income_txs = transactions.filter(type='income')
        expense_txs = transactions.filter(type='expense')
        
        total_income = sum(t.amount for t in income_txs)
        total_expense = sum(t.amount for t in expense_txs)
        
        items_list = ""
        for t in transactions:
            data_fmt = t.transaction_date.strftime('%d/%m')
            tipo_fmt = 'GANHO' if t.type == 'income' else 'GASTO'
            items_list += f"- [{data_fmt}] ID: {t.identifier} | {t.description} | {t.category} | R$ {t.amount:.2f} ({tipo_fmt})\n"

        context = f"PERÍODO: {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}\n"
        if category_filter:
            context += f"CATEGORIA FILTRADA: {category_filter}\n"
        
        context += f"\nMOVIMENTAÇÕES:\n{items_list if items_list else 'Nenhuma encontrada.'}\n"
        context += f"\nRESUMO:\n- Ganhos: R$ {total_income:.2f}\n- Gastos: R$ {total_expense:.2f}\n- Saldo: R$ {total_income - total_expense:.2f}"

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

            # Se a IA identificar que faltam informações, ela não agenda
            if data.get('missing_info') or not data.get('title') or not data.get('date'):
                # Tentar recuperar informações da mensagem original se a extração falhar
                # Isso ajuda se o modelo for muito rígido
                return "Com certeza! Para agendar, preciso saber *o que* é o compromisso e *qual dia/horário*. \n\nExemplo: 'Dentista amanhã às 14h'."
            
            # Combinar data e hora
            time_str = data.get('time') or "09:00"
            dt_str = f"{data.get('date')} {time_str}"
            dt_obj = timezone.make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M'))
            
            appt = Appointment.objects.create(
                user=user,
                title=data.get('title', 'Compromisso'),
                date_time=dt_obj
            )
            
            response = f"📅 **COMPROMISSO AGENDADO!**\n\n"
            response += f"📌 **O quê:** {appt.title}\n"
            response += f"🕒 **Quando:** {dt_obj.strftime('%d/%m/%Y às %H:%M')}\n"
            response += f"🆔 **ID:** `{appt.identifier}`\n\n"
            response += f"🚀 _Eu te avisarei quando estiver chegando a hora! Para remover ou editar, use o ID_ `{appt.identifier}`."
            return response
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
