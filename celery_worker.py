import os
import requests
from celery import Celery
from ai_service import get_smart_proposal
from web_generator import generate_page
from pdf_generator import generate_pdf
from database import update_proposal_with_data
import logging
import time # Добавлено для time.sleep (если нужно)

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Переменная REDIS_URL не найдена!")

celery_app = Celery('tasks', broker=redis_url, backend=redis_url)

# НОВАЯ ЗАДАЧА: Отправка сообщения (она ждет 10 секунд в фоне, не мешая остальным)
@celery_app.task
def task_send_result(chat_id: int, proposal_id: int, web_url: str, pdf_filename: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # 1. Отправляем текст и ссылку
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
        "chat_id": chat_id,
        "text": f"✅ Готово! Проект #{proposal_id}

🌐 Интерактивная 3D-версия: {web_url}
📄 PDF-версия для печати прикреплена ниже 👇",
        "parse_mode": "HTML"
    })
    
    # 2. Отправляем PDF
    if os.path.exists(pdf_filename):
        with open(pdf_filename, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendDocument", data={
                "chat_id": chat_id
            }, files={"document": f})
        
        # 3. Чистим за собой сервер (удаляем PDF после отправки)
        os.remove(pdf_filename) 
    return True

# ОСНОВНАЯ ЗАДАЧА (Теперь работает молниеносно)
@celery_app.task
def task_generate_proposal(proposal_id: int, client: str, task: str, chat_id: int):
    logger.info(f"🔄 [Worker] Начинаю генерацию для КП #{proposal_id}")
    
    proposal_data = get_smart_proposal(task)
    
    if proposal_data:
        update_proposal_with_data(proposal_id, proposal_data)
        generate_page(proposal_id, client, task, proposal_data)
        
        pdf_filename = f"proposal_{proposal_id}.pdf"
        generate_pdf(proposal_data, pdf_filename, str(proposal_id))
        
        web_url = f"https://coolmag.github.io/KPbot/proposals/{proposal_id}.html"
        
        # МАГИЯ АСИНХРОННОСТИ: Отправляем сообщение через 10 секунд!
        task_send_result.apply_async(args=[chat_id, proposal_id, web_url, pdf_filename], countdown=10)
        
        logger.info(f"✅ [Worker] КП #{proposal_id} сгенерировано. Отправка клиенту через 10 секунд...")
        return True
        
    logger.error(f"❌ [Worker] Ошибка AI-генерации для КП #{proposal_id}")
    return False