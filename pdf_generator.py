from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os

def create_proposal_pdf(text_content):
    """
    Создает PDF-документ с коммерческим предложением из текста.
    Возвращает байтовый объект PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # 1. Регистрируем шрифт с поддержкой кириллицы
    font_path = "DejaVuSans.ttf"

    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
            font_name = 'DejaVuSans'
        else:
            font_name = 'Helvetica'  # Fallback (кириллица не будет работать)
            print(f"Warning: Font file {font_path} not found.")
    except Exception as e:
        font_name = 'Helvetica'
        print(f"Font error: {e}")

    styles = getSampleStyleSheet()

    # 2. Создаем стиль с нашим шрифтом
    cyrillic_style = ParagraphStyle(
        'CyrillicStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=12,
        leading=16,
        spaceAfter=10
    )

    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=20,
        alignment=1  # Center
    )

    story = []

    # Добавим заголовок
    story.append(Paragraph("Коммерческое предложение", header_style))
    story.append(Spacer(1, 12))

    # Обработка текста
    for line in text_content.split('<br/>'):
        if line.strip():
            story.append(Paragraph(line, cyrillic_style))
        else:
            story.append(Spacer(1, 6))

    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


if __name__ == '__main__':
    # Пример для тестирования модуля
    sample_text = "Коммерческое предложение<br/><br/>Уважаемый клиент,<br/><br/>Представляем вам наше предложение по услуге разработки Telegram-бота."
    pdf_data = create_proposal_pdf(sample_text)
    with open("sample_proposal.pdf", "wb") as f:
        f.write(pdf_data)
    print("Тестовый PDF 'sample_proposal.pdf' успешно создан.")

