# 🧠 Agente Financeiro - SaaS com IA

Sistema SaaS financeiro com agente via WhatsApp, dashboard web e controle de assinaturas.

## 📋 Funcionalidades

- ✅ **Autenticação de Usuários** com email e telefone
- ✅ **Sistema de Assinaturas** integrado com Kirvano
- ✅ **Agente IA via WhatsApp** para registrar transações
- ✅ **Dashboard Web** para visualizar e gerenciar finanças
- ✅ **Webhooks** para Kirvano e WhatsApp
- ✅ **Histórico de Alterações** em transações

## 🛠️ Stack Tecnológica

- **Backend**: Django 6.0
- **Templates**: Django Templates
- **IA**: LangChain + OpenAI
- **Mensagens**: Twilio (WhatsApp)
- **Pagamento**: Kirvano
- **Database**: SQLite (desenvolvimento) / PostgreSQL (produção)
- **Cache/Queue**: Redis + Celery

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone <seu-repositorio>
cd AGENTE\ FINANCEIRO
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas chaves de API.

### 5. Execute as migrações

```bash
python manage.py migrate
```

### 6. Crie um superusuário

```bash
python manage.py createsuperuser
```

### 7. Execute o servidor

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

## 📁 Estrutura do Projeto

```
AGENTE FINANCEIRO/
├── accounts/           # Autenticação e usuários
├── subscriptions/      # Sistema de assinaturas
├── transactions/       # Transações financeiras
├── agents/            # Agentes de IA (LangChain)
├── webhooks/          # Endpoints de webhooks
├── dashboard/         # Dashboard web
├── whatsapp_messages/ # Mensagens do WhatsApp
├── core/              # Configurações do Django
├── templates/         # Templates HTML
├── static/            # Arquivos estáticos
└── manage.py
```

## 🔄 Fluxo do Sistema

### 1. Compra e Ativação
1. Usuário compra assinatura
2. Webhook Kirvano recebe evento
3. Sistema cria usuário e ativa assinatura
4. Envia mensagem WhatsApp com link de ativação
5. Usuário cria senha e ativa conta

### 2. Uso do Agente WhatsApp
1. Usuário envia mensagem via WhatsApp
2. Sistema valida assinatura ativa
3. Normaliza mensagem (texto/áudio/imagem)
4. Router IA identifica intenção
5. Subagente processa (criar/editar/deletar/relatório)
6. Salva no banco de dados
7. Responde ao usuário

### 3. Dashboard Web
1. Usuário faz login
2. Visualiza transações e relatórios
3. Pode editar/deletar manualmente
4. Dados sincronizados com agente WhatsApp

## 🔐 Segurança

- ✅ Validação de tokens em webhooks
- ✅ Prevenção de duplicação de eventos (event_id)
- ✅ Validação de usuário por telefone
- ✅ Rate limiting (a implementar)
- ✅ CSRF protection
- ✅ Senhas hasheadas

## 📊 Modelos de Dados

### User
- Email (único)
- Telefone (único)
- Nome
- Senha

### Subscription
- Usuário
- ID Kirvano
- Plano
- Status (active/pending/canceled/expired)
- Datas de início e expiração

### Transaction
- Usuário
- Identificador único (TX-XXXXX)
- Descrição
- Categoria
- Valor
- Tipo (receita/despesa)
- Data da transação

### Message
- Usuário
- Tipo (texto/áudio/imagem)
- Conteúdo original
- Texto normalizado
- Status
- Intenção identificada

### WebhookEvent
- Origem (Kirvano/WhatsApp)
- ID do evento
- Tipo de evento
- Payload
- Status de processamento

## 🚀 Próximos Passos

- [ ] Implementar webhooks (Kirvano e WhatsApp)
- [ ] Criar sistema de autenticação e ativação
- [ ] Desenvolver agentes de IA com LangChain
- [ ] Implementar debounce de mensagens
- [ ] Criar dashboard web com templates
- [ ] Adicionar gráficos e relatórios
- [ ] Implementar Celery para tarefas assíncronas
- [ ] Adicionar testes unitários
- [ ] Deploy em produção

## 📝 Licença

MIT

## 👨‍💻 Autor

André - Desenvolvedor Full Stack
