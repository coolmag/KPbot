import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black, white, lightgrey
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate_pdf(proposal_data: dict, filename: str, proposal_id: str):
    font_path = "assets/fonts/DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
    else:
        print("⚠️ ШРИФТ НЕ НАЙДЕН")
        return False

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Строгие цвета
    BRAND_COLOR = HexColor("#1A252F") # Темно-синий
    ACCENT = HexColor("#C5A059") # Золотой
    TEXT_DARK = HexColor("#333333")

    def draw_header(page):
        c.setFillColor(BRAND_COLOR)
        c.rect(0, height - 60, width, 60, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("DejaVu", 16)
        c.drawString(40, height - 40, "KOTEL.MSK.RU")
        c.setFont("DejaVu", 10)
        c.drawRightString(width - 40, height - 40, f"Проект #{proposal_id} | Стр. {page}")

    # --- СТРАНИЦА 1: ТИТУЛЬНЫЙ ЛИСТ ---
    draw_header(1)
    
    c.setFillColor(TEXT_DARK)
    c.setFont("DejaVu", 28)
    c.drawString(40, height - 150, "ТЕХНИКО-КОММЕРЧЕСКОЕ")
    c.drawString(40, height - 190, "ПРЕДЛОЖЕНИЕ")
    
    c.setFillColor(ACCENT)
    c.rect(40, height - 210, 100, 4, stroke=0, fill=1)

    c.setFillColor(TEXT_DARK)
    c.setFont("DejaVu", 12)
    
    # Краткое резюме от ИИ
    summary = proposal_data.get("executive_summary", "Проект системы отопления")
    c.drawString(40, height - 260, "Описание задачи:")
    
    c.setFont("DejaVu", 10)
    c.setFillColor(HexColor("#555555"))
    # Простой перенос длинного текста
    import textwrap
    lines = textwrap.wrap(summary, width=80)
    y_pos = height - 280
    for line in lines[:5]: # Максимум 5 строк
        c.drawString(40, y_pos, line)
        y_pos -= 15

    # --- СТРАНИЦА 2: СМЕТА ---
    c.showPage()
    draw_header(2)
    
    c.setFillColor(TEXT_DARK)
    c.setFont("DejaVu", 18)
    c.drawString(40, height - 120, "ДЕТАЛИЗАЦИЯ СМЕТЫ (Варианты)")

    y_position = height - 160
    plans = proposal_data.get("plans", [])

    for plan in plans:
        # Заголовок тарифа
        c.setFillColor(BRAND_COLOR)
        c.rect(40, y_position - 20, width - 80, 25, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("DejaVu", 12)
        c.drawString(50, y_position - 15, f"ВАРИАНТ: {plan.get('name', '').upper()}")
        
        # Цена
        c.setFillColor(ACCENT)
        c.setFont("DejaVu", 12)
        c.drawRightString(width - 50, y_position - 15, str(plan.get("total_price", "")))
        
        y_position -= 40
        
        # Позиции
        c.setFont("DejaVu", 9)
        for item in plan.get("budget_items", []):
            c.setFillColor(HexColor("#eeeeee"))
            c.rect(40, y_position - 12, width - 80, 15, stroke=0, fill=1) # Зебра
            
            c.setFillColor(TEXT_DARK)
            c.drawString(50, y_position - 8, str(item.get("item", ""))[:70])
            c.drawRightString(width - 50, y_position - 8, str(item.get("price", "")))
            y_position -= 16

        y_position -= 30 # Отступ между тарифами
        if y_position < 100:
            c.showPage()
            draw_header(3)
            y_position = height - 100

    c.save()
    return True
