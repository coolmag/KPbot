# celery_worker.py
import os
import requests
from celery import Celery
from ai_service import get_smart_proposal
from web_generator import generate_page
from pdf_generator import generate_pdf
from database import update_proposal_with_data
import logging

logger = logging.getLogger(__name__)

# Подключаемся к Redis (по умолчанию локальный)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery('tasks', broker=redis_url)

@celery_app.task
def task_generate_proposal(proposal_id: int, client: str, task: str, chat_id: int):
    logger.info(f"🔄 [Worker] Начинаю генерацию для КП #{proposal_id}")
    
    # 1. Нейросеть генерирует данные
    proposal_data = get_smart_proposal(task)
    
    if proposal_data:
        # 2. Сохраняем в базу и делаем WEB-версию
        update_proposal_with_data(proposal_id, proposal_data)
        generate_page(proposal_id, client, task, proposal_data)
        
        # 3. ДЕЛАЕМ PDF-ВЕРСИЮ
        pdf_filename = f"proposal_{proposal_id}.pdf"
        generate_pdf(proposal_data, pdf_filename) # Вызываем вашу старую добрую функцию
        
        # 4. Отправляем результаты обратно менеджеру в Telegram (через API)
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        web_url = f"https://coolmag.github.io/KPbot/proposals/{proposal_id}.html"
        
        # Отправляем текст со ссылкой
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"""✅ Готово! Проект #{proposal_id}

🌐 Интерактивная 3D-версия: {web_url}
📄 PDF-версия для печати прикреплена ниже 👇""",
            "parse_mode": "HTML"
        })
        
        # Отправляем сам PDF файл прямо в чат!
        try:
            with open(pdf_filename, "rb") as f:
                requests.post(f"https://api.telegram.org/bot{bot_token}/sendDocument", data={
                    "chat_id": chat_id
                }, files={"document": f})
        finally:
            # Удаляем временный файл PDF после отправки
            if os.path.exists(pdf_filename):
                os.remove(pdf_filename)
            
        logger.info(f"✅ [Worker] КП #{proposal_id} (WEB + PDF) успешно отправлено!")
        return True
    
    logger.error(f"❌ [Worker] Ошибка AI-генерации для КП #{proposal_id}")
    return False
