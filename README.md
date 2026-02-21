# 🤖 Agente Prime - Ecossistema SaaS com IA

O **Agente Prime** é uma solução SaaS completa de gestão financeira e pessoal, que integra o poder da Inteligência Artificial (GPT-4o) diretamente no WhatsApp, combinada com um Dashboard Web robusto para controle total do usuário.

## 🚀 Funcionalidades Principais

### 📱 Inteligência Artificial via WhatsApp
- **Processamento de Linguagem Natural**: Anote gastos e ganhos conversando naturalmente com o agente.
- **🖼️ Visão Computacional (OCR)**: Envie fotos de comprovantes, notas fiscais ou prints de Pix para registro automático.
- **🎤 Transcrição de Áudio (Whisper)**: Envie áudios descrevendo suas transações e a IA cuidará do resto.
- **📅 Sistema de Agendamento Inteligente**: Marque reuniões, lembretes ou consultas via chat. O sistema envia notificações automáticas via WhatsApp (1 hora e 5 minutos antes).
- **📊 Relatórios Instantâneos**: Peça resumos financeiros, saldos ou listagens diretamente pelo WhatsApp.
- **✍️ Edição e Exclusão Segura**: Gerencie registros existentes usando IDs curtos de 3 caracteres (Ex: `A1B`).

### 💻 Dashboard Web Profissional
- **Visão Geral**: Gráficos dinâmicos de evolução de saldo e distribuição de gastos por categoria.
- **Gestão de Transações**: Filtre, pesquise, extraia, edite ou exclua lançamentos manualmente.
- **Agenda de Compromissos**: Visualize e gerencie seus compromissos em uma interface limpa.
- **📄 Exportações Profissionais**: Gere relatórios em **PDF** com gráficos ou exporte todos os dados para **Excel**.
- **Gestão de Perfil**: Controle seus dados de acesso e preferências.

### 💳 Infraestrutura SaaS
- **Sistema de Assinaturas**: Integração nativa com **Kirvano** (ativação automática pós-compra).
- **Onboarding Automático**: Criação de conta e envio de dados de acesso via WhatsApp no momento da aprovação do pagamento.
- **Controle de Acesso**: Bloqueio automático de funções de IA para usuários com assinaturas expiradas ou canceladas.

## 🛠️ Stack Tecnológica

- **Backend**: Django 5.x (Python)
- **IA**: OpenAI API (GPT-4o-mini, Whisper, Vision) + LangChain
- **Mensagens & WhatsApp**: Evolution API v2
- **Pagamentos**: Kirvano Webhooks
- **Fila de Tarefas**: Celery + Redis (para notificações agendadas e tarefas de fundo)
- **Database**: PostgreSQL (Produção) / SQLite (Desenvolvimento)
- **Design**: Vanilla CSS com Estética Premium e Responsiva

## ⚙️ Configuração do Ambiente

### 1. Requisitos
- Python 3.10+
- Redis Server
- Chave de API OpenAI
- Instância da Evolution API

### 2. Instalação
```bash
git clone https://github.com/seu-user/agente-prime.git
cd agente-prime
python -m venv venv
source venv/bin/activate # ou venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente (.env)
Crie um arquivo `.env` na raiz do projeto:
```env
DEBUG=True
SECRET_KEY=sua_secret_key
OPENAI_API_KEY=sk-...
EVOLUTION_BASE_URL=https://sua-instancia.com
EVOLUTION_API_KEY=sua_apikey
EVOLUTION_INSTANCE=AgentePrime
KIRVANO_WEBHOOK_SECRET=seu_token
SITE_URL=https://seu-dominio.com
```

### 4. Execução
```bash
python manage.py migrate
python manage.py runserver
```

## 📁 Estrutura do Projeto
- `agents/`: Lógica central da IA, prompts e roteamento de intenções.
- `agenda/`: Sistema de agendamentos e notificações Celery.
- `transactions/`: Core financeiro (modelos e lógica de identificadores).
- `whatsapp_messages/`: Integração com Evolution API e logs de mensagens.
- `webhooks/`: Endpoints para integração com Kirvano e WhatsApp.
- `dashboard/`: Views e utilitários para a interface web e exportação de documentos.

## 🔐 Segurança e Confiabilidade
- **Timezone**: Configurado para `America/Sao_Paulo` em todos os níveis.
- **Deduplicação**: Proteção contra processamento duplo de webhooks via IDs de evento únicos.
- **Identificadores**: IDs compactos (3 caracteres) para facilitar a interação via chat.
- **Logs**: Rastreamento completo de mudanças em campos sensíveis de transações.

---
## 👨‍💻 Desenvolvedor
Desenvolvido por **André** - Transformando IA em ferramentas práticas para o dia a dia.

---
*Este projeto é um SaaS pronto para produção, focado em UX excepcional e automação inteligente.*
