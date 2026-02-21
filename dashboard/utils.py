import io
import pandas as pd
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from django.utils import timezone

def generate_transactions_excel(transactions):
    """
    Gera um arquivo Excel com a lista de transações fornecida.
    """
    data = []
    for tx in transactions:
        data.append({
            'Data': tx.transaction_date.strftime('%d/%m/%Y'),
            'Identificador': tx.identifier,
            'Descrição': tx.description,
            'Categoria': tx.category,
            'Tipo': 'Receita' if tx.type == 'income' else 'Despesa',
            'Valor (R$)': float(tx.amount)
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transações')
        
        # Ajustar largura das colunas (opcional, mas deixa mais "profissional")
        # workbook = writer.book
        # worksheet = writer.sheets['Transações']
        # ... (mais complexo sem saber se openpyxl está totalmente configurado)
        
    output.seek(0)
    return output

def generate_transactions_pdf(user, transactions, summary_data):
    """
    Gera um PDF profissional com resumo, gráficos e tabela de transações.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para títulos
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#2563eb"), # Azul moderno
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor("#1e293b"),
    )

    # 1. Cabeçalho
    elements.append(Paragraph("Relatório Financeiro Profissional", title_style))
    elements.append(Paragraph(f"Usuário: {user.nome or user.email}", styles["Normal"]))
    elements.append(Paragraph(f"Período: {summary_data.get('date_range', 'Geral')}", styles["Normal"]))
    elements.append(Paragraph(f"Data de Geração: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.2 * inch))

    # 2. Resumo Financeiro
    elements.append(Paragraph("Resumo do Período", subtitle_style))
    
    summary_table_data = [
        ["Total de Receitas", "Total de Despesas", "Saldo Final"],
        [
            f"R$ {summary_data['income_total']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
            f"R$ {summary_data['expense_total']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','),
            f"R$ {summary_data['balance']:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        ]
    ]
    
    s_table = Table(summary_table_data, colWidths=[2 * inch] * 3)
    s_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#64748b")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.darkgreen), # Receitas
        ('TEXTCOLOR', (1, 1), (1, 1), colors.red),       # Despesas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(s_table)
    elements.append(Spacer(1, 0.3 * inch))

    # 3. Gráficos (Fluxo de Caixa)
    elements.append(Paragraph("Distribuição de Gastos por Categoria", subtitle_style))
    
    # Gerar gráfico com Matplotlib
    if summary_data['expense_data']:
        plt.figure(figsize=(6, 4))
        plt.pie(summary_data['expense_data'], labels=summary_data['expense_labels'], autopct='%1.1f%%', 
                colors=plt.cm.Paired.colors, startangle=140)
        plt.title('Despesas por Categoria')
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        report_img = Image(img_buffer, width=4*inch, height=3*inch)
        elements.append(report_img)
    else:
        elements.append(Paragraph("Sem dados de despesas para exibir o gráfico.", styles["Italic"]))
    
    elements.append(Spacer(1, 0.3 * inch))

    # 4. Tabela de Transações Detalhada
    elements.append(Paragraph("Detalhamento de Transações", subtitle_style))
    
    tx_data = [["Data", "Descrição", "Categoria", "Tipo", "Valor"]]
    for tx in transactions[:50]: # Limitar a 50 para o PDF não ficar gigante, se precisar mais o usuário usa Excel
        tx_data.append([
            tx.transaction_date.strftime('%d/%m/%Y'),
            tx.description[:30],
            tx.category,
            'Receita' if tx.type == 'income' else 'Despesa',
            f"R$ {tx.amount:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
        ])
    
    t = Table(tx_data, colWidths=[0.8*inch, 2.2*inch, 1.2*inch, 0.8*inch, 1.0*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Colorir linhas alternadamente ou por tipo
    for i in range(1, len(tx_data)):
        if tx_data[i][3] == 'Receita':
            t.setStyle(TableStyle([('TEXTCOLOR', (4, i), (4, i), colors.darkgreen)]))
        else:
            t.setStyle(TableStyle([('TEXTCOLOR', (4, i), (4, i), colors.red)]))

    elements.append(t)
    
    if len(transactions) > 50:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"* Exibindo apenas as primeiras 50 de {len(transactions)} transações. Para o relatório completo, utilize a exportação em Excel.", styles["Italic"]))

    # Finalizar PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
