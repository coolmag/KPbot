from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from io import BytesIO
import logging
import datetime
from utils import ensure_font_exists

logger = logging.getLogger(__name__)

# --- 📝 ТВОИ КОНТАКТЫ (ЗАПОЛНИ ЭТО!) ---
COMPANY_NAME = "KOTEL.MSK.RU"
CONTACT_PHONE = "+7 (999) 123-45-67"  # <-- Твой телефон
CONTACT_EMAIL = "info@kotel.msk.ru"   # <-- Твой email
CONTACT_SITE = "https://kotel.msk.ru"
MANAGER_NAME = "Александр"            # <-- Имя менеджера в подписи
# ---------------------------------------

# Цвета
COLOR_PRIMARY = colors.HexColor("#1A252F")
COLOR_ACCENT = colors.HexColor("#C5A059")
COLOR_TEXT_MAIN = colors.HexColor("#2C3E50")
COLOR_TEXT_LIGHT = colors.HexColor("#7F8C8D")
COLOR_BG_LIGHT = colors.HexColor("#F9FAFB")

def register_fonts():
    font_path = ensure_font_exists()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('AppFont', font_path))
            return 'AppFont'
        except Exception: pass
    return 'Helvetica'

def on_page(canvas, doc):
    canvas.saveState()
    # Линия
    canvas.setStrokeColor(COLOR_ACCENT)
    canvas.setLineWidth(2)
    canvas.line(0, A4[1] - 0.5*cm, A4[0], A4[1] - 0.5*cm)
    # Водяной знак
    canvas.setFont('AppFont', 50)
    canvas.setFillColor(colors.HexColor("#000000"), alpha=0.03)
    canvas.translate(A4[0]/2, A4[1]/2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, COMPANY_NAME)
    canvas.restoreState()
    
    # Футер
    canvas.saveState()
    canvas.setFont('AppFont', 8)
    canvas.setFillColor(COLOR_TEXT_LIGHT)
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, f"Страница {doc.page}")
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.drawString(2*cm, 1*cm, f"{COMPANY_NAME} | {CONTACT_PHONE}")
    canvas.restoreState()

def create_cover_page(story, styles, font_name, data):
    story.append(Spacer(1, 4*cm))
    style_logo = ParagraphStyle('Logo', parent=styles['Normal'], fontName=font_name, fontSize=32, textColor=COLOR_PRIMARY, alignment=TA_CENTER, leading=40)
    story.append(Paragraph(f"<b>{COMPANY_NAME}</b>", style_logo))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f'<font color="{COLOR_ACCENT.hexval()}">▬▬▬▬▬▬▬▬▬▬▬▬▬▬</font>', style_logo))
    story.append(Spacer(1, 3*cm))
    style_cover_title = ParagraphStyle('CoverTitle', parent=styles['Normal'], fontName=font_name, fontSize=24, textColor=COLOR_PRIMARY, alignment=TA_CENTER, leading=32)
    story.append(Paragraph(data.get('title', 'Коммерческое Предложение'), style_cover_title))
    story.append(Spacer(1, 1*cm))
    style_meta = ParagraphStyle('CoverMeta', parent=styles['Normal'], fontName=font_name, fontSize=12, textColor=COLOR_TEXT_LIGHT, alignment=TA_CENTER)
    date_str = datetime.datetime.now().strftime("%d.%m.%Y")
    story.append(Paragraph(f"Дата: {date_str}", style_meta))
    story.append(PageBreak())

def generate_pdf(data: dict, filename: str):
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)
    font_name = register_fonts()
    styles = getSampleStyleSheet()

    style_h1 = ParagraphStyle('LuxuryH1', parent=styles['Heading1'], fontName=font_name, fontSize=18, textColor=COLOR_PRIMARY, spaceBefore=20, spaceAfter=10, borderColor=COLOR_ACCENT, borderWidth=0)
    style_body = ParagraphStyle('LuxuryBody', parent=styles['Normal'], fontName=font_name, fontSize=11, leading=16, textColor=COLOR_TEXT_MAIN, alignment=TA_JUSTIFY, spaceAfter=10)
    style_quote = ParagraphStyle('Quote', parent=style_body, backColor=COLOR_BG_LIGHT, borderPadding=15, borderRadius=5, textColor=COLOR_PRIMARY)

    story = []
    create_cover_page(story, styles, font_name, data)

    # Контент
    if data.get('executive_summary'):
        story.append(Paragraph("О ПРОЕКТЕ", style_h1))
        story.append(Paragraph(f"<i>{data['executive_summary']}</i>", style_quote))
        story.append(Spacer(1, 1*cm))

    if data.get('client_pain_points'):
        story.append(Paragraph("ЗАДАЧИ", style_h1))
        for p in data['client_pain_points']:
            story.append(Paragraph(f"<font color={COLOR_ACCENT.hexval()}>✔</font> {p}", style_body))
        story.append(Spacer(1, 0.5*cm))

    if data.get('solution_steps'):
        story.append(Paragraph("РЕШЕНИЕ", style_h1))
        for i, s in enumerate(data['solution_steps'], 1):
            story.append(Paragraph(f"<font color={COLOR_PRIMARY.hexval()}><b>{i:02d}. {s.get('step_name')}</b></font>", style_body))
            story.append(Paragraph(s.get('description'), style_body))
            story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())

    if data.get("plans"):

        story.append(Paragraph("ИНВЕСТИЦИОННЫЙ РАСЧЕТ", style_h1))
        story.append(Spacer(1, 0.5*cm))

        for plan in data["plans"]:

            story.append(Paragraph(plan["name"].upper(), style_h1))
            story.append(Paragraph(plan.get("description", ""), style_body))

            table_data = [["НАИМЕНОВАНИЕ", "СРОК", "СТОИМОСТЬ"]]

            for item in plan["budget_items"]:

                table_data.append([
                    Paragraph(item.get("item", ""), style_body),
                    Paragraph(item.get("time", "-"), style_body),
                    Paragraph(f"<b>{item.get('price', '-')}</b>", style_body)
                ])

            t = Table(table_data, colWidths=[10*cm, 2.5*cm, 3.5*cm])

            t.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), font_name),
                ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,0), 2, COLOR_ACCENT),
            ]))

            story.append(t)
            story.append(Spacer(1, 1*cm))

    # --- КОНТАКТНЫЙ БЛОК В КОНЦЕ ---
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph("КОНТАКТЫ", style_h1))
    
    contact_style = ParagraphStyle('Contact', parent=style_body, fontSize=12, alignment=TA_LEFT)
    
    # Таблица контактов для красоты
    contact_data = [
        ["Менеджер проекта:", MANAGER_NAME],
        ["Телефон:", CONTACT_PHONE],
        ["Email:", CONTACT_EMAIL],
        ["Сайт:", CONTACT_SITE]
    ]
    
    ct = Table(contact_data, colWidths=[5*cm, 10*cm])
    ct.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), font_name),
        ('TEXTCOLOR', (0,0), (-1,-1), COLOR_PRIMARY),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(ct)
    
    story.append(Spacer(1, 1*cm))
    link_text = f'<a href="{CONTACT_SITE}" color="#C5A059"><u>ОСТАВИТЬ ЗАЯВКУ НА САЙТЕ</u></a>'
    story.append(Paragraph(link_text, ParagraphStyle('Link', parent=style_body, alignment=TA_CENTER)))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)