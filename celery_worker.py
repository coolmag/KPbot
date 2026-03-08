import os
import requests
from celery import Celery
from ai_service import get_smart_proposal
from web_generator import generate_page
from pdf_generator import generate_pdf
from database import update_proposal_with_data

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Переменная REDIS_URL не найдена!")

celery_app = Celery('tasks', broker=redis_url, backend=redis_url)

@celery_app.task
def task_send_result(chat_id: int, proposal_id: int, web_url: str, pdf_filename: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # 🛠️ ИСПРАВЛЕНИЕ ЗДЕСЬ: Текст собран в одну безопасную строку
    msg_text = f"✅ Готово! Проект #{proposal_id}

🌐 Инженерная схема и смета: {web_url}
📄 Строгий PDF для печати прикреплен ниже 👇"
    
    # 1. Отправляем текст и ссылку
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
        "chat_id": chat_id,
        "text": msg_text,
        "parse_mode": "HTML"
    })
    
    # 2. Отправляем PDF
    if os.path.exists(pdf_filename):
        with open(pdf_filename, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendDocument", data={
                "chat_id": chat_id
            }, files={"document": f})
        
        # 3. Удаляем PDF после отправки, чтобы не забивать память
        os.remove(pdf_filename) 
    return True

@celery_app.task
def task_generate_proposal(proposal_id: int, client: str, task: str, chat_id: int):
    print(f"🔄 [Worker] Начинаю генерацию для КП #{proposal_id}")
    
    proposal_data = get_smart_proposal(task)
    
    if proposal_data:
        # Сохраняем в БД
        update_proposal_with_data(proposal_id, proposal_data)
        
        # Генерируем сайт-чертеж
        generate_page(proposal_id, client, task, proposal_data)
        
        # Генерируем строгий PDF
        pdf_filename = f"proposal_{proposal_id}.pdf"
        generate_pdf(proposal_data, pdf_filename, str(proposal_id))
        
        web_url = f"https://coolmag.github.io/KPbot/proposals/{proposal_id}.html"
        
        # Отправляем сообщение через 10 секунд (чтобы GitHub Pages успел обновить кэш)
        task_send_result.apply_async(args=[chat_id, proposal_id, web_url, pdf_filename], countdown=10)
        
        print(f"✅ [Worker] КП #{proposal_id} сгенерировано. Отправка клиенту через 10 секунд...")
        return True
        
    print(f"❌ [Worker] Ошибка AI-генерации для КП #{proposal_id}")
    return False