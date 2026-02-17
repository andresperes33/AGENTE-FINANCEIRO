# Configuração de E-mail para Produção (SMTP)

Para que o "Esqueci minha senha" funcione no site real, você precisa configurar um servidor que envia os e-mails.

## Opção 1: Usando Gmail (Gratuito e Fácil)
Se você tem uma conta Gmail, pode gerar uma "Senha de App" para enviar e-mails pelo sistema.

1. Acesse sua conta Google: https://myaccount.google.com/
2. Vá em **Segurança** > **Verificação em duas etapas** (ative se não estiver).
3. Busque por **Senhas de app** (App Passwords).
4. Crie uma nova senha com nome "Agente Financeiro".
5. Copie a senha de 16 caracteres gerada.

**No EasyPanel (Variáveis de Ambiente):**
Adicione estas chaves:
- `EMAIL_HOST`: smtp.gmail.com
- `EMAIL_PORT`: 587
- `EMAIL_USE_TLS`: True
- `EMAIL_HOST_USER`: seu.email@gmail.com
- `EMAIL_HOST_PASSWORD`: a_senha_de_app_gerada_aqui
- `DEFAULT_FROM_EMAIL`: Agente Prime <seu.email@gmail.com>

---

## Opção 2: Usando Brevo (Antigo Sendinblue) - Profissional Gratuito
Recomendado para evitar cair no SPAM. O plano gratuito permite 300 e-mails/dia.

1. Crie conta no [Brevo](https://www.brevo.com/).
2. Vá em Configurações > SMTP & API.
3. Gere uma nova chave SMTP.

**No EasyPanel:**
- `EMAIL_HOST`: smtp-relay.brevo.com
- `EMAIL_PORT`: 587
- `EMAIL_USE_TLS`: True
- `EMAIL_HOST_USER`: seu_login_brevo@email.com
- `EMAIL_HOST_PASSWORD`: sua_chave_smtp_brevo
- `DEFAULT_FROM_EMAIL`: Agente Prime <seu_email_validado@dominio.com>
