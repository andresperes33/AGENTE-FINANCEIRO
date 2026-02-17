# INSTRUCOES PARA CORRIGIR O ERRO 500 NA RECUPERACAO DE SENHA

## PROBLEMA ATUAL:
O erro 500 acontece quando o usuário clica em "Enviar Instruções" porque o Django não consegue enviar o e-mail via Gmail.

## CAUSAS POSSÍVEIS:
1. Senha de app do Gmail incorreta (a de 16 caracteres)
2. Gmail bloqueando o app
3. Credenciais erradas em EMAIL_HOST_USER ou EMAIL_HOST_PASSWORD

## SOLUÇÃO TEMPORÁRIA PARA TESTAR:

### Opção 1: Usar Console Backend (Recomendado para teste)
No EasyPanel, **REMOVA** ou **COMENTE** estas variáveis temporariamente:
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_USE_TLS
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- DEFAULT_FROM_EMAIL

Isso fará o Django imprimir o link de recuperação nos logs em vez de enviar e-mail.

**Como usar:**
1. Remova as variáveis acima no EasyPanel
2. Reinicie o serviço
3. Clique em "Esqueci minha senha"
4. Digite um e-mail
5. Vá nos LOGS do EasyPanel
6. Você verá o LINK de recuperação impresso lá
7. Copie o link e acesse

---

## SOLUÇÃO DEFINITIVA:

### Verifique a Senha de App do Gmail:
1. Acesse: https://myaccount.google.com/apppasswords
2. Gere uma NOVA senha de app (caso a antiga esteja errada)
3. Copie a senha (vem em formato: abcd efgh ijkl mnop)
4. **IMPORTANTE:** Cole SEM ESPAÇOS: abcdefghijklmnop

### Configure corretamente no EasyPanel:
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=andrecode.py@gmail.com
EMAIL_HOST_PASSWORD=suasenhadeapp16caracteres
DEFAULT_FROM_EMAIL=Agente Prime <andrecode.py@gmail.com>
```

### Teste o envio de e-mail:
Após configurar, teste novamente.

Se ainda der erro, os LOGS vão mostrar:
- "SMTPAuthenticationError" = senha errada
- "SMTPServerDisconnected" = Gmail bloqueou
- Outro erro específico que ajuda a diagnosticar
