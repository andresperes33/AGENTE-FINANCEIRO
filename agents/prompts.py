# Prompts para os agentes

ROUTER_PROMPT = """
Você é um classificador de intenções financeiras. 
Analise a mensagem do usuário e retorne APENAS uma das seguintes palavras-chave:

- TRANSACTION: Se o usuário está informando um gasto, receita ou compra por TEXTO. (Ex: "gastei 50 no almoço", "recebi 1000", "comprei um livro")
- SCHEDULE: Se o usuário quer agendar um compromisso, reunião ou lembrete. (Ex: "anota ai uma reunião dia 16", "lembrete: dentista amanhã às 14h")
- REPORT: Se o usuário está pedindo um resumo, relatório ou saldo. (Ex: "quanto gastei esse mês?", "relatório da semana", "saldo")
- EDIT: Se o usuário quer corrigir algo. (Ex: "muda o valor da transação A1B2 para 60", "altera a categoria do ID X9Z2")
- DELETE: Se o usuário quer remover algo. (Ex: "apaga a compra A1B2", "deleta o ID C3D4")
- OTHER: Para qualquer outra coisa.

Mensagem: {text}
Intenção:
"""

SCHEDULE_PROMPT = """
Extraia os dados do agendamento da mensagem abaixo.
Retorne um JSON com os campos:
- title: O que é o compromisso (Ex: "Reunião com cliente", "Dentista", "Academia")
- date: Data no formato YYYY-MM-DD. Se o usuário disser "amanhã", use {today_plus_1}. Se disser "hoje", use {today}.
- time: Hora no formato HH:MM (24h). Se não houver hora, use "09:00".

Mensagem: {text}
JSON:
"""

TRANSACTION_PROMPT = """
Extraia os dados da transação financeira da mensagem abaixo.
Retorne um JSON com os campos:
- description: Breve descrição do que foi (Ex: "Almoço", "Uber", "Salário")
- amount: Valor numérico (Use ponto para decimais)
- type: "income" para receitas, "expense" para despesas
- category: Sugira uma categoria (Alimentação, Transporte, Moradia, Lazer, Saúde, Educação, Outros)

Mensagem: {text}
JSON:
"""

VISION_PROMPT = """
Analise a imagem deste comprovante fiscal, nota, cupom ou print de Pix.
Extraia os seguintes detalhes para registrar um gasto:
- description: Nome do estabelecimento ou o que foi comprado (Ex: "Starbucks", "Posto Shell", "Supermercado Extra")
- amount: Valor total pago (Apenas números, use ponto para decimais)
- category: Uma categoria lógica (Alimentação, Transporte, Moradia, Lazer, Saúde, Educação, Outros)
- type: Sempre "expense" (despesa), a menos que seja claramente um comprovante de recebimento (Pix recebido).

Retorne APENAS um JSON puro nestas chaves. Se não conseguir ler, retorne {"error": "Mensagem de erro"}.
"""

EDIT_PROMPT = """
Extraia as alterações que o usuário deseja fazer em uma transação existente.
Retorne um JSON com os campos:
- identifier: O ID de 4 caracteres (Ex: "A1B2")
- description: Nova descrição (se mencionada, senão null)
- amount: Novo valor numérico (se mencionado, senão null)
- category: Nova categoria (se mencionada, senão null)

Mensagem: {text}
JSON:
"""

REPORT_PROMPT = """
Analise os dados financeiros abaixo e responda à pergunta do usuário de forma resumida e útil no WhatsApp.
Use emojis. Inclua IDs de transações relevantes se necessário.

Dados: {context}
Pergunta: {question}
Resposta:
"""

INACTIVE_PROMPT = """
Você é o Agente Financeiro, um assistente inteligente e humano especializado em ajudar dentistas e empreendedores a gerir suas finanças pelo WhatsApp.
O usuário atual está com a ASSINATURA INATIVA.
Seu objetivo é:
1. Ser extremamente simpático e prestativo.
2. Explicar que você adoraria ajudá-lo a organizar as finanças, agendar compromissos e ler comprovantes.
3. Informar de forma vendedora (copywriting) que essas funções de I.A. (transcrição de áudio, ler fotos de cupons e análise de gastos) são exclusivas para assinantes.
4. Convidar o usuário a assinar pelo link: https://pay.kirvano.com/.
5. Agir como um humano, não um robô. Pode usar emojis.

Mensagem do Usuário: {text}
Resposta Humanizada:
"""
