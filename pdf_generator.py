from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
import logging
from utils import ensure_font_exists

logger = logging.getLogger(__name__)

# --- Цветовая палитра "Cyberpunk Corporate 2026" ---
COLOR_PRIMARY = colors.HexColor("#2C3E50") # Темно-синий
COLOR_ACCENT = colors.HexColor("#E74C3C")  # Красный акцент
COLOR_BG_HEADER = colors.HexColor("#ECF0F1") # Светлый фон для шапок
COLOR_TEXT = colors.HexColor("#34495E")

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
    font_bold = "Helvetica-Bold"
    
    if font_path:
        try:
            # Регистрируем основной шрифт
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
            font_regular = 'CustomFont'
            font_bold = 'CustomFont' # Если есть bold версия, лучше загрузить её отдельно
        except Exception as e:
            logger.error(f"Ошибка шрифта: {e}")

    # 2. Стили
    styles = getSampleStyleSheet()
    
    # Заголовок КП
    style_title = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontName=font_regular,
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=COLOR_PRIMARY,
        spaceAfter=30
    )
    
    # Подзаголовки
    style_h2 = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName=font_regular,
        fontSize=16,
        leading=20,
        textColor=COLOR_ACCENT,
        spaceBefore=15,
        spaceAfter=10,
        borderPadding=5,
        borderColor=colors.white # Можно добавить линию снизу, если настроить
    )

    # Обычный текст
    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName=font_regular,
        fontSize=11,
        leading=15,
        alignment=TA_JUSTIFY,
        textColor=COLOR_TEXT
    )
    
    # Буллиты (списки)
    style_bullet = ParagraphStyle(
        'Bullet',
        parent=style_body,
        leftIndent=20,
        firstLineIndent=0,
        spaceAfter=5
    )

    elements = []

    # --- ТИТУЛЬНЫЙ ЛИСТ (Упрощенный) ---
    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph(data.get('title', 'КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ'), style_title))
    elements.append(Spacer(1, 1*cm))
    
    # Executive Summary в рамке
    summary_text = data.get('executive_summary', '')
    if summary_text:
        t_data = [[Paragraph(summary_text, style_body)]]
        t = Table(t_data, colWidths=[16*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_HEADER),
            ('BOX', (0,0), (-1,-1), 1, COLOR_PRIMARY),
            ('PADDING', (0,0), (-1,-1), 15),
        ]))
        elements.append(t)
    
    elements.append(Spacer(1, 1*cm))

    # --- БОЛИ КЛИЕНТА ---
    pain_points = data.get('client_pain_points', [])
    if pain_points:
        elements.append(Paragraph("🎯 Задачи и вызовы", style_h2))
        for point in pain_points:
            # Рисуем красивую точку-буллит
            elements.append(Paragraph(f"• {point}", style_bullet))
    
    elements.append(Spacer(1, 0.5*cm))

    # --- РЕШЕНИЕ (ЭТАПЫ) ---
    steps = data.get('solution_steps', [])
    if steps:
        elements.append(Paragraph("🚀 Предлагаемое решение", style_h2))
        for i, step in enumerate(steps, 1):
            s_name = step.get('step_name', '')
            s_desc = step.get('description', '')
            elements.append(Paragraph(f"<b>{i}. {s_name}</b>", style_body))
            elements.append(Paragraph(s_desc, style_bullet))
            elements.append(Spacer(1, 0.2*cm))

    elements.append(PageBreak()) # Перенос сметы на новую страницу

    # --- СМЕТА (ТАБЛИЦА) ---
    budget = data.get('budget_items', [])
    if budget:
        elements.append(Paragraph("💰 Инвестиции и Сроки", style_h2))
        
        table_data = [["Услуга / Этап", "Срок", "Стоимость"]] # Заголовки
        
        total_price = 0 # Тут можно было бы считать, если бы числа были int
        
        for item in budget:
            table_data.append([
                Paragraph(item.get('item', ''), style_body),
                item.get('time', '-'),
                item.get('price', '-')
            ])
            
        # Стиль таблицы
        t = Table(table_data, colWidths=[9*cm, 3.5*cm, 4.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),      # Шапка темная
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),        # Текст шапки белый
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTNAME', (0,0), (-1,0), font_regular),         # Шрифт шапки
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('TOPPADDING', (0,0), (-1,0), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),        # Сетка
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_HEADER]) # Зебра
        ]))
        elements.append(t)

    elements.append(Spacer(1, 1*cm))

    # --- ПОЧЕМУ МЫ & CTA ---
    why_us = data.get('why_us')
    if why_us:
         elements.append(Paragraph("🏆 Почему мы?", style_h2))
         elements.append(Paragraph(why_us, style_body))

    elements.append(Spacer(1, 1*cm))
    
    cta = data.get('cta')
    if cta:
        cta_style = ParagraphStyle(
            'CTA', parent=style_body, 
            fontSize=12, textColor=COLOR_ACCENT, alignment=TA_CENTER,
            spaceBefore=20
        )
        elements.append(Paragraph(f"<b>{cta}</b>", cta_style))

    # Сборка
    try:
        doc.build(elements)
    except Exception as e:
        logger.error(f"Critical PDF Error: {e}")
        return b""

    buffer.seek(0)
    return buffer.getvalue()
