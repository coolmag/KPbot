from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
import logging
from utils import ensure_font_exists

logger = logging.getLogger(__name__)

# Цвета бренда
COLOR_PRIMARY = colors.HexColor("#2C3E50") 
COLOR_ACCENT = colors.HexColor("#E74C3C")  
COLOR_BG_HEADER = colors.HexColor("#ECF0F1")
COLOR_TEXT = colors.HexColor("#34495E")

def add_watermark(canvas, doc):
    """Рисует водяной знак и футер на каждой странице"""
    canvas.saveState()
    
    # --- ВОДЯНОЙ ЗНАК ---
    canvas.setFont("Helvetica-Bold", 60)
    canvas.setFillColor(colors.grey, alpha=0.1) # Прозрачность 10%
    canvas.translate(10*cm, 15*cm) # Центр страницы
    canvas.rotate(45) # Поворот на 45 градусов
    canvas.drawCentredString(0, 0, "KOTEL.MSK.RU")
    
    canvas.restoreState()
    
    # --- ФУТЕР С ССЫЛКОЙ ---
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#7F8C8D"))
    
    footer_text = "Профессиональный монтаж отопления | KOTEL.MSK.RU"
    
    # Рисуем текст по центру внизу
    canvas.drawCentredString(A4[0]/2, 1*cm, footer_text)
    
    # Делаем "KOTEL.MSK.RU" кликабельной ссылкой
    # (Примерно вычисляем координаты ссылки, это не идеально точно, но работает)
    link_x = A4[0]/2 + 40 # Смещение вправо от центра
    link_width = 80
    
    # canvas.linkURL("https://kotel.msk.ru", (rect_x1, rect_y1, rect_x2, rect_y2))
    # Но проще сделать весь футер ссылкой, если не заморачиваться с координатами
    
    canvas.restoreState()

def create_proposal_pdf(data: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    # 1. Шрифты
    font_path = ensure_font_exists()
    font_regular = "Helvetica"
    
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
            font_regular = 'CustomFont'
        except Exception as e:
            logger.error(f"Ошибка шрифта: {e}")

    # 2. Стили
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'MainTitle', parent=styles['Heading1'], fontName=font_regular,
        fontSize=24, leading=30, alignment=TA_CENTER, textColor=COLOR_PRIMARY, spaceAfter=30
    )
    
    style_h2 = ParagraphStyle(
        'H2', parent=styles['Heading2'], fontName=font_regular,
        fontSize=16, leading=20, textColor=COLOR_ACCENT, spaceBefore=15, spaceAfter=10
    )

    style_body = ParagraphStyle(
        'Body', parent=styles['Normal'], fontName=font_regular,
        fontSize=11, leading=15, alignment=TA_JUSTIFY, textColor=COLOR_TEXT
    )
    
    style_link = ParagraphStyle(
        'Link', parent=style_body, textColor=colors.blue, alignment=TA_CENTER
    )

    elements = []

    # ТИТУЛ
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(data.get('title', 'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ'), style_title))
    
    # Ссылка под заголовком
    link = '<a href="https://kotel.msk.ru" color="blue"><u>https://kotel.msk.ru</u></a>'
    elements.append(Paragraph(link, style_link))
    elements.append(Spacer(1, 1*cm))
    
    # СУТЬ
    summary = data.get('executive_summary', '')
    if summary:
        t = Table([[Paragraph(summary, style_body)]], colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_HEADER),
            ('BOX', (0,0), (-1,-1), 1, COLOR_PRIMARY),
            ('PADDING', (0,0), (-1,-1), 15),
        ]))
        elements.append(t)
    
    elements.append(Spacer(1, 1*cm))

    # БОЛИ
    pain = data.get('client_pain_points', [])
    if pain:
        elements.append(Paragraph("🎯 Задачи", style_h2))
        for p in pain:
            elements.append(Paragraph(f"• {p}", style_body))
    
    elements.append(Spacer(1, 0.5*cm))

    # РЕШЕНИЕ
    steps = data.get('solution_steps', [])
    if steps:
        elements.append(Paragraph("🚀 Решение", style_h2))
        for i, s in enumerate(steps, 1):
            name = s.get('step_name', '')
            desc = s.get('description', '')
            elements.append(Paragraph(f"<b>{i}. {name}</b>", style_body))
            elements.append(Paragraph(desc, style_body))
            elements.append(Spacer(1, 0.2*cm))

    elements.append(PageBreak())

    # СМЕТА
    budget = data.get('budget_items', [])
    if budget:
        elements.append(Paragraph("💰 Смета (Ориентировочно)", style_h2))
        table_data = [["Услуга", "Срок", "Стоимость"]]
        for item in budget:
            table_data.append([
                Paragraph(item.get('item', ''), style_body),
                item.get('time', '-'),
                item.get('price', '-')
            ])
            
        t = Table(table_data, colWidths=[9*cm, 3.5*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), font_regular),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_HEADER])
        ]))
        elements.append(t)

    elements.append(Spacer(1, 1*cm))
    
    # CTA
    cta = data.get('cta')
    if cta:
        elements.append(Paragraph(f"<b>{cta}</b>", style_body))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Заявки на сайте: " + link, style_body))

    try:
        # ВАЖНО: передаем функцию onFirstPage и onLaterPages для отрисовки водяного знака
        doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
    except Exception as e:
        logger.error(f"PDF Error: {e}")
        return b""

    buffer.seek(0)
    return buffer.getvalue()