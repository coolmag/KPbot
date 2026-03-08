import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode

def generate_pdf(proposal_data: dict, filename: str, proposal_id: str):
    # Регистрируем шрифт (Убедитесь, что DejaVuSans.ttf лежит в assets/fonts/)
    font_path = "assets/fonts/DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
    else:
        print("⚠️ ШРИФТ НЕ НАЙДЕН, PDF МОЖЕТ БЫТЬ С ОШИБКАМИ")
        return False

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Фирменные цвета 2026
    DARK_BG = HexColor("#0B0F19")
    CARD_BG = HexColor("#151A28")
    GOLD = HexColor("#C5A059")
    TEXT_LIGHT = HexColor("#E2E8F0")

    def draw_background():
        """Заливка страницы премиальным темным цветом"""
        c.setFillColor(DARK_BG)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        
    def draw_footer(page_num):
        c.setFont("DejaVu", 9)
        c.setFillColor(TEXT_LIGHT)
        c.drawString(40, 30, "KOTEL.MSK.RU | Инженерные системы премиум-класса")
        c.drawRightString(width - 40, 30, f"Стр. {page_num}")

    # ================= СТРАНИЦА 1: ОБЛОЖКА =================
    draw_background()
    
    # Декоративная золотая линия
    c.setFillColor(GOLD)
    c.rect(0, height - 150, 8, 100, stroke=0, fill=1)

    # Логотип / Название
    c.setFont("DejaVu", 36)
    c.setFillColor(white)
    c.drawString(50, height - 100, "KOTEL.MSK.RU")
    c.setFont("DejaVu", 12)
    c.setFillColor(GOLD)
    c.drawString(50, height - 120, "ИНТЕЛЛЕКТУАЛЬНОЕ КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ")

    # Кому
    c.setFont("DejaVu", 24)
    c.setFillColor(white)
    c.drawString(50, height - 250, "Проект котельной")
    c.setFont("DejaVu", 16)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(50, height - 280, f"Подготовлено для ID: #{proposal_id}")

    # Генерация QR-Кода
    qr_url = f"https://coolmag.github.io/KPbot/proposals/{proposal_id}.html"
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#C5A059", back_color="#0B0F19")
    qr_filename = f"qr_temp_{proposal_id}.png"
    img.save(qr_filename)

    # Вставляем QR-код
    c.drawImage(qr_filename, 50, height - 550, width=150, height=150)
    c.setFont("DejaVu", 12)
    c.setFillColor(white)
    c.drawString(220, height - 450, "← НАВЕДИТЕ КАМЕРУ ТЕЛЕФОНА")
    c.setFont("DejaVu", 10)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(220, height - 470, "Чтобы открыть 3D-модель объекта и")
    c.drawString(220, height - 485, "пообщаться с голосовым AI-инженером")

    draw_footer(1)
    c.showPage()

    # ================= СТРАНИЦА 2: СМЕТА И ТАРИФЫ =================
    draw_background()
    
    c.setFont("DejaVu", 24)
    c.setFillColor(GOLD)
    c.drawString(40, height - 80, "ВАРИАНТЫ РЕАЛИЗАЦИИ")

    y_position = height - 140
    plans = proposal_data.get("plans", [])

    for plan in plans:
        # Рисуем подложку тарифа (Карточку)
        c.setFillColor(CARD_BG)
        c.rect(40, y_position - 120, width - 80, 130, stroke=0, fill=1)
        
        # Название тарифа
        c.setFont("DejaVu", 16)
        c.setFillColor(white)
        c.drawString(60, y_position - 20, plan.get("name", "Тариф").upper())
        
        # Описание
        c.setFont("DejaVu", 10)
        c.setFillColor(TEXT_LIGHT)
        # Разбиваем длинное описание на 2 строки
        desc = plan.get("description", "")
        c.drawString(60, y_position - 40, desc[:80])
        if len(desc) > 80:
            c.drawString(60, y_position - 55, desc[80:160] + "...")

        # Итоговая цена
        c.setFont("DejaVu", 20)
        c.setFillColor(GOLD)
        c.drawRightString(width - 60, y_position - 30, str(plan.get("total_price", "")))

        # Позиции (бюджет)
        y_item = y_position - 80
        c.setFont("DejaVu", 10)
        for item in plan.get("budget_items", [])[:2]: # Показываем только топ-2 позиции для красоты
            c.setFillColor(TEXT_LIGHT)
            c.drawString(60, y_item, "• " + str(item.get("item", ""))[:50])
            c.setFillColor(white)
            c.drawRightString(width - 60, y_item, str(item.get("price", "")))
            y_item -= 20

        y_position -= 150 # Отступ для следующего тарифа

        if y_position < 150:
            draw_footer(2)
            c.showPage()
            draw_background()
            y_position = height - 100

    draw_footer(2)
    
    c.save()
    
    # Удаляем временный QR
    if os.path.exists(qr_filename):
        os.remove(qr_filename)
        
    return True
