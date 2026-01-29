from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Frame, PageTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Line
from io import BytesIO
import logging
import datetime
from utils import ensure_font_exists

logger = logging.getLogger(__name__)

# --- LUXURY PALETTE ---
COLOR_PRIMARY = colors.HexColor("#1A252F")  # Глубокий темно-синий (почти черный)
COLOR_ACCENT = colors.HexColor("#C5A059")   # Матовое золото (не желтое, а благородное)
COLOR_TEXT_MAIN = colors.HexColor("#2C3E50")
COLOR_TEXT_LIGHT = colors.HexColor("#7F8C8D")
COLOR_BG_LIGHT = colors.HexColor("#F9FAFB") # Очень светлый фон для блоков

def register_fonts():
    """Регистрирует шрифты. Если нет Bold версии, используем Regular."""
    font_path = ensure_font_exists()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('AppFont', font_path))
            return 'AppFont'
        except Exception as e:
            logger.error(f"Font Error: {e}")
    return 'Helvetica'

def on_page(canvas, doc):
    """Отрисовка фона и декоративных элементов на каждой странице"""
    canvas.saveState()
    
    # 1. Золотая линия сверху
    canvas.setStrokeColor(COLOR_ACCENT)
    canvas.setLineWidth(2)
    canvas.line(0, A4[1] - 0.5*cm, A4[0], A4[1] - 0.5*cm)

    # 2. Водяной знак (ОЧЕНЬ прозрачный и стильный)
    canvas.setFont('AppFont', 50)
    canvas.setFillColor(colors.HexColor("#000000"), alpha=0.03) # 3% прозрачности
    canvas.translate(A4[0]/2, A4[1]/2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "KOTEL.MSK.RU")
    
    canvas.restoreState()
    
    # 3. Футер (Номер страницы и копирайт)
    canvas.saveState()
    canvas.setFont('AppFont', 8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    
    page_num = f"Страница {doc.page}"
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, page_num)
    
    # Ссылка слева
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.drawString(2*cm, 1*cm, "KOTEL.MSK.RU | Инженерные системы")
    canvas.restoreState()

def create_cover_page(story, styles, font_name, data):
    """Создает премиальную обложку"""
    story.append(Spacer(1, 4*cm))
    
    # Логотип (текстовый, раз нет картинки)
    style_logo = ParagraphStyle(
        'Logo', parent=styles['Normal'], fontName=font_name, 
        fontSize=32, textColor=COLOR_PRIMARY, alignment=TA_CENTER, leading=40
    )
    story.append(Paragraph("<b>KOTEL.MSK.RU</b>", style_logo))
    
    # Декоративная линия
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f'<font color="{COLOR_ACCENT.hexval()}">▬▬▬▬▬▬▬▬▬▬▬▬▬▬</font>', style_logo))
    story.append(Spacer(1, 3*cm))
    
    # Название КП
    style_cover_title = ParagraphStyle(
        'CoverTitle', parent=styles['Normal'], fontName=font_name,
        fontSize=24, textColor=COLOR_PRIMARY, alignment=TA_CENTER, leading=32
    )
    story.append(Paragraph(data.get('title', 'Коммерческое Предложение'), style_cover_title))
    
    story.append(Spacer(1, 1*cm))
    
    # Дата и инфо
    style_meta = ParagraphStyle(
        'CoverMeta', parent=styles['Normal'], fontName=font_name,
        fontSize=12, textColor=COLOR_TEXT_LIGHT, alignment=TA_CENTER
    )
    date_str = datetime.datetime.now().strftime("%d.%m.%Y")
    story.append(Paragraph(f"Дата формирования: {date_str}", style_meta))
    story.append(Paragraph("Статус: Индивидуальный проект", style_meta))
    
    story.append(PageBreak())

def create_proposal_pdf(data: dict) -> bytes:
    buffer = BytesIO()
    
    # Отступы стали больше для "воздуха"
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2.5*cm, leftMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm
    )

    font_name = register_fonts()
    styles = getSampleStyleSheet()

    # --- СТИЛИ ---
    # Заголовки разделов
    style_h1 = ParagraphStyle(
        'LuxuryH1', parent=styles['Heading1'], fontName=font_name,
        fontSize=18, textColor=COLOR_PRIMARY, spaceBefore=20, spaceAfter=10,
        borderPadding=10, borderColor=COLOR_ACCENT, borderWidth=0,
        backColor=None # Можно включить фон
    )
    
    # Обычный текст
    style_body = ParagraphStyle(
        'LuxuryBody', parent=styles['Normal'], fontName=font_name,
        fontSize=11, leading=16, textColor=COLOR_TEXT_MAIN, alignment=TA_JUSTIFY,
        spaceAfter=10
    )

    # Цитата / Важное (для Executive Summary)
    style_quote = ParagraphStyle(
        'Quote', parent=style_body,
        backColor=COLOR_BG_LIGHT, borderPadding=15,
        borderWidth=0, borderRadius=5,
        leftIndent=10, rightIndent=10,
        textColor=COLOR_PRIMARY
    )

    story = []

    # 1. ОБЛОЖКА
    create_cover_page(story, styles, font_name, data)

    # 2. Executive Summary (Суть)
    summary = data.get('executive_summary', '')
    if summary:
        story.append(Paragraph("О ПРОЕКТЕ", style_h1))
        # Золотая линия под заголовком
        story.append(Spacer(1, 2))
        
        story.append(Paragraph(f"<i>{summary}</i>", style_quote))
        story.append(Spacer(1, 1*cm))

    # 3. Боли (Client Pain Points)
    pain = data.get('client_pain_points', [])
    if pain:
        story.append(Paragraph("ЗАДАЧИ И РИСКИ", style_h1))
        for p in pain:
            # Используем красивые галочки вместо точек
            story.append(Paragraph(f"<font color={COLOR_ACCENT.hexval()}>✔</font> {p}", style_body))
        story.append(Spacer(1, 0.5*cm))

    # 4. Решение
    steps = data.get('solution_steps', [])
    if steps:
        story.append(Paragraph("ТЕХНИЧЕСКОЕ РЕШЕНИЕ", style_h1))
        for i, s in enumerate(steps, 1):
            name = s.get('step_name', '')
            desc = s.get('description', '')
            # Заголовок шага жирным и синим
            story.append(Paragraph(f"<font color={COLOR_PRIMARY.hexval()}><b>{i:02d}. {name}</b></font>", style_body))
            story.append(Paragraph(desc, style_body))
            story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())

    # 5. Смета (Luxury Table)
    budget = data.get('budget_items', [])
    if budget:
        story.append(Paragraph("ИНВЕСТИЦИОННЫЙ РАСЧЕТ", style_h1))
        story.append(Spacer(1, 0.5*cm))

        table_data = [["НАИМЕНОВАНИЕ УСЛУГИ / ОБОРУДОВАНИЯ", "СРОК", "СТОИМОСТЬ"]]
        for item in budget:
            table_data.append([
                Paragraph(item.get('item', ''), style_body),
                Paragraph(item.get('time', '-'), style_body),
                Paragraph(f"<b>{item.get('price', '-')}</b>", style_body) # Цена жирным
            ])

        # Настройка таблицы (Modern Clean Style)
        t = Table(table_data, colWidths=[10*cm, 2.5*cm, 3.5*cm])
        
        t.setStyle(TableStyle([
            # Шрифты
            ('FONTNAME', (0,0), (-1,-1), font_name),
            
            # Шапка
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('TOPPADDING', (0,0), (-1,0), 12),
            
            # Тело таблицы
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,1), (-1,-1), 10),
            ('TOPPADDING', (0,1), (-1,-1), 10),
            
            # Линии (Только горизонтальные!)
            ('LINEBELOW', (0,0), (-1,0), 2, COLOR_ACCENT), # Золотая линия под шапкой
            ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor("#E0E0E0")), # Тонкие серые линии
            
            # Убираем вертикальные линии для "воздуха"
            ('BOX', (0,0), (-1,-1), 0, colors.white), 
        ]))
        story.append(t)
        
        # Примечание под таблицей
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("* Цены указаны ориентировочно и могут быть скорректированы после выезда инженера.", 
                               ParagraphStyle('Note', parent=style_body, fontSize=8, textColor=COLOR_TEXT_LIGHT)))

    # 6. Почему мы & CTA
    story.append(Spacer(1, 1*cm))
    why_us = data.get('why_us')
    if why_us:
        # Выделяем блок "Почему мы" рамкой
        story.append(Paragraph("ПОЧЕМУ ВЫБИРАЮТ НАС", style_h1))
        story.append(Paragraph(why_us, style_body))

    story.append(Spacer(1, 1.5*cm))
    
    cta = data.get('cta')
    if cta:
        # CTA как кнопка
        style_cta = ParagraphStyle(
            'CTA', parent=style_body,
            fontSize=12, textColor=COLOR_PRIMARY, alignment=TA_CENTER,
            borderWidth=1, borderColor=COLOR_ACCENT, borderPadding=10,
            borderRadius=5
        )
        story.append(Paragraph(f"<b>{cta}</b>", style_cta))
        
        link = '<a href="https://kotel.msk.ru" color="#C5A059"><u>ОСТАВИТЬ ЗАЯВКУ НА САЙТЕ</u></a>'
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(link, ParagraphStyle('Link', parent=style_body, alignment=TA_CENTER)))

    # Генерация
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    
    buffer.seek(0)
    return buffer.getvalue()