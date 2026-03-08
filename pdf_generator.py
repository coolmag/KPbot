import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import textwrap

# --- КОНТАКТЫ КОМПАНИИ ---
COMPANY_NAME = os.getenv("COMPANY_NAME", "KOTEL.MSK.RU")
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "+7 (495) 123-45-67")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "info@kotel.msk.ru")
CONTACT_SITE = os.getenv("CONTACT_SITE", "www.kotel.msk.ru")
MANAGER_NAME = os.getenv("MANAGER_NAME", "Главный инженер")

# --- ЦВЕТА ---
COLOR_PRIMARY = colors.HexColor("#1A252F")
COLOR_ACCENT = colors.HexColor("#C5A059")
COLOR_TEXT = colors.HexColor("#333333")
COLOR_GRAY = colors.HexColor("#7F8C8D")
COLOR_LIGHT_GRAY = colors.HexColor("#ECF0F1")
COLOR_BG = colors.HexColor("#FAFAFA")

class PDFGenerator:
    def __init__(self, filename, proposal_id):
        self.filename = filename
        self.proposal_id = proposal_id
        self.doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=3.5*cm,
            bottomMargin=3*cm
        )
        self.elements = []
        self._register_fonts()
        self._setup_styles()

    def _register_fonts(self):
        font_path = "assets/fonts/DejaVuSans.ttf"
        font_bold_path = "assets/fonts/DejaVuSans-Bold.ttf"
        
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVu', font_path))
            if os.path.exists(font_bold_path):
                pdfmetrics.registerFont(TTFont('DejaVu-Bold', font_bold_path))
            else:
                pdfmetrics.registerFont(TTFont('DejaVu-Bold', font_path))
        else:
            print("⚠️ ОШИБКА: ШРИФТ НЕ НАЙДЕН. PDF МОЖЕТ БЫТЬ СКОМПИЛИРОВАН С ОШИБКАМИ КИРИЛЛИЦЫ.")

    def _setup_styles(self):
        self.styles = getSampleStyleSheet()
        
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            fontName='DejaVu-Bold',
            fontSize=32,
            textColor=COLOR_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=1*cm
        ))
        
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            fontName='DejaVu',
            fontSize=16,
            textColor=COLOR_GRAY,
            alignment=TA_CENTER,
            spaceAfter=2*cm
        ))

        self.styles.add(ParagraphStyle(
            name='H1',
            fontName='DejaVu-Bold',
            fontSize=20,
            textColor=COLOR_PRIMARY,
            spaceAfter=0.5*cm,
            spaceBefore=1*cm
        ))

        self.styles.add(ParagraphStyle(
            name='H2',
            fontName='DejaVu-Bold',
            fontSize=16,
            textColor=COLOR_ACCENT,
            spaceAfter=0.3*cm,
            spaceBefore=0.5*cm
        ))

        self.styles.add(ParagraphStyle(
            name='NormalText',
            fontName='DejaVu',
            fontSize=10,
            textColor=COLOR_TEXT,
            leading=14,
            spaceAfter=0.3*cm,
            alignment=TA_JUSTIFY
        ))

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        
        # Header (Top Banner)
        canvas.setFillColor(COLOR_PRIMARY)
        canvas.rect(0, height - 2*cm, width, 2*cm, stroke=0, fill=1)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('DejaVu-Bold', 14)
        canvas.drawString(2*cm, height - 1.2*cm, COMPANY_NAME)
        
        canvas.setFont('DejaVu', 10)
        canvas.drawRightString(width - 2*cm, height - 1.2*cm, f"Коммерческое предложение №{self.proposal_id}")

        # Footer (Bottom Banner)
        canvas.setFillColor(COLOR_BG)
        canvas.rect(0, 0, width, 1.5*cm, stroke=0, fill=1)
        
        canvas.setFillColor(COLOR_GRAY)
        canvas.setFont('DejaVu', 8)
        canvas.drawString(2*cm, 0.6*cm, f"{CONTACT_PHONE}  |  {CONTACT_EMAIL}  |  {CONTACT_SITE}")
        
        page_num = canvas.getPageNumber()
        canvas.drawRightString(width - 2*cm, 0.6*cm, f"Страница {page_num}")
        
        # Watermark
        canvas.setFillColor(COLOR_LIGHT_GRAY)
        canvas.setStrokeColor(COLOR_LIGHT_GRAY)
        canvas.setFont('DejaVu-Bold', 80)
        canvas.saveState()
        canvas.translate(width/2, height/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, COMPANY_NAME)
        canvas.restoreState()
        
        canvas.restoreState()

    def build_cover(self, data):
        self.elements.append(Spacer(1, 3*cm))
        self.elements.append(Paragraph("ТЕХНИКО-КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", self.styles['CoverTitle']))
        
        date_str = datetime.now().strftime("%d.%m.%Y")
        self.elements.append(Paragraph(f"Проект котельной #{self.proposal_id}<br/>от {date_str}", self.styles['CoverSubtitle']))
        
        self.elements.append(Spacer(1, 4*cm))
        
        contact_info = f"""
        <b>Исполнитель:</b> {COMPANY_NAME}<br/>
        <b>Телефон:</b> {CONTACT_PHONE}<br/>
        <b>Email:</b> {CONTACT_EMAIL}<br/>
        <b>Менеджер:</b> {MANAGER_NAME}
        """
        self.elements.append(Paragraph(contact_info, self.styles['NormalText']))
        self.elements.append(PageBreak())

    def build_summary(self, data):
        self.elements.append(Paragraph("РЕЗЮМЕ ПРОЕКТА", self.styles['H1']))
        
        summary_text = data.get("executive_summary", "Система разработана с учетом современных стандартов энергоэффективности и надежности.")
        self.elements.append(Paragraph(summary_text, self.styles['NormalText']))
        
        # Pain points
        pains = data.get("client_pain_points", [])
        if pains:
            self.elements.append(Paragraph("Решаемые задачи:", self.styles['H2']))
            for pain in pains:
                self.elements.append(Paragraph(f"• {pain}", self.styles['NormalText']))
                
        self.elements.append(PageBreak())

    def build_plans(self, data):
        self.elements.append(Paragraph("ВАРИАНТЫ КОМПЛЕКТАЦИИ (СМЕТА)", self.styles['H1']))
        
        plans = data.get("plans", [])
        for plan in plans:
            self.elements.append(Paragraph(f"Конфигурация: {plan.get('name', 'Базовый').upper()}", self.styles['H2']))
            desc = plan.get('description', '')
            if desc:
                self.elements.append(Paragraph(desc, self.styles['NormalText']))
            
            self.elements.append(Spacer(1, 0.3*cm))
            
            # Таблица сметы
            table_data = [["Наименование оборудования / работ", "Стоимость"]]
            items = plan.get("budget_items", [])
            for item in items:
                # Оборачиваем длинный текст
                wrapped_text = Paragraph(str(item.get("item", "")), self.styles['NormalText'])
                table_data.append([wrapped_text, str(item.get("price", ""))])
            
            # Строка Итого
            table_data.append(["ИТОГО ПО КОНФИГУРАЦИИ:", str(plan.get("total_price", ""))])
            
            # Стили таблицы
            t = Table(table_data, colWidths=[12*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                # Zebra
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, COLOR_LIGHT_GRAY]),
                # Итоговая строка
                ('BACKGROUND', (0, -1), (-1, -1), COLOR_ACCENT),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                ('FONTNAME', (0, -1), (-1, -1), 'DejaVu-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
                ('GRID', (0,0), (-1,-1), 0.5, colors.white),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            
            self.elements.append(t)
            self.elements.append(Spacer(1, 1*cm))

    def generate(self, data):
        self.build_cover(data)
        self.build_summary(data)
        self.build_plans(data)
        
        try:
            self.doc.build(self.elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
            return True
        except Exception as e:
            print(f"❌ Ошибка генерации PDF: {e}")
            return False

def generate_pdf(proposal_data: dict, filename: str, proposal_id: str):
    generator = PDFGenerator(filename, proposal_id)
    return generator.generate(proposal_data)
