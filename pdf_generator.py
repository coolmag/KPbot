from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import logging
from utils import ensure_font_exists

logger = logging.getLogger(__name__)

def create_proposal_pdf(text_content: str) -> bytes:
    """
    Создает PDF-документ. Функция блокирующая (CPU-bound).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=72, leftMargin=72, 
        topMargin=72, bottomMargin=72
    )
    
    # Инициализация шрифта через утилиту
    font_path = ensure_font_exists()
    font_name = 'Helvetica' # Fallback по умолчанию

    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
            font_name = 'DejaVuSans'
        except Exception as e:
            logger.error(f"Не удалось зарегистрировать шрифт: {e}")
    else:
        logger.warning("Используется стандартный шрифт (кириллица может не отображаться).")

    styles = getSampleStyleSheet()

    # Стили
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        leading=15,
        spaceAfter=10
    )

    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        spaceAfter=20,
        alignment=1, # Center
        textColor='#2c3e50'
    )

    story = []
    story.append(Paragraph("Коммерческое предложение", header_style))
    story.append(Spacer(1, 12))

    # Обработка переносов строк для ReportLab
    # Заменяем \n на <br/>, так как ReportLab использует XML-подобную разметку
    clean_text = text_content.replace('\n', '<br/>')
    
    story.append(Paragraph(clean_text, normal_style))
    
    # Добавляем футер
    story.append(Spacer(1, 30))
    footer_text = "Сгенерировано автоматически с помощью AI Client Pilot"
    footer_style = ParagraphStyle(
        'Footer', 
        parent=normal_style, 
        fontSize=8, 
        textColor='gray', 
        alignment=1
    )
    story.append(Paragraph(footer_text, footer_style))

    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"Ошибка сборки PDF: {e}", exc_info=True)
        return b""
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes