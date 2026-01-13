from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
from io import BytesIO

def create_proposal_pdf(text_content):
    """
    Создает PDF-документ с коммерческим предложением из текста.
    Возвращает байтовый объект PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    styles = getSampleStyleSheet()
    # Пока используем простой стиль. Позже можно будет добавить кириллические шрифты.
    story = [Paragraph(line.replace(' ', '&nbsp;'), styles["Normal"]) for line in text_content.split('\n')]
    
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

if __name__ == '__main__':
    # Пример для тестирования модуля
    sample_text = "Коммерческое предложение\n\nУважаемый клиент,\n\nПредставляем вам наше предложение."
    pdf_data = create_proposal_pdf(sample_text)
    with open("sample_proposal.pdf", "wb") as f:
        f.write(pdf_data)
    print("Тестовый PDF 'sample_proposal.pdf' успешно создан.")

