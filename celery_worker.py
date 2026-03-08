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
    
    # 🟢 ЖЕЛЕЗОБЕТОННЫЙ ФОРМАТ: обычное сложение строк
    part1 = "✅ Готово! Проект #" + str(proposal_id) + "\n\n"
    part2 = "🌐 Инженерная схема и смета: " + str(web_url) + "\n"
    part3 = "📄 Строгий PDF для печати прикреплен ниже 👇"
    msg_text = part1 + part2 + part3
    
    # 1. Отправляем текст и ссылку
    requests.post("https://api.telegram.org/bot" + str(bot_token) + "/sendMessage", json={
        "chat_id": chat_id,
        "text": msg_text,
        "parse_mode": "HTML"
    })
    
    # 2. Отправляем PDF
    if os.path.exists(pdf_filename):
        with open(pdf_filename, "rb") as f:
            requests.post("https://api.telegram.org/bot" + str(bot_token) + "/sendDocument", data={
                "chat_id": chat_id
            }, files={"document": f})
        
        # 3. Удаляем PDF после отправки
        os.remove(pdf_filename) 
    return True

@celery_app.task
def task_generate_proposal(proposal_id: int, client: str, task: str, chat_id: int, media_path: str = None, media_type: str = "text"):
    print(f"🔄 [Worker] Начинаю генерацию для КП #{proposal_id} (Type: {media_type})")
    
    proposal_data = get_smart_proposal(task, media_path, media_type)
    
    if media_path and os.path.exists(media_path):
        try:
            os.remove(media_path)
            print(f"🧹 [Worker] Временный файл {media_path} удален.")
        except Exception as e:
            print(f"⚠️ [Worker] Не удалось удалить {media_path}: {e}")
            
    if proposal_data:
        update_proposal_with_data(proposal_id, proposal_data)
        generate_page(proposal_id, client, task, proposal_data)
        
        pdf_filename = f"proposal_{proposal_id}.pdf"
        generate_pdf(proposal_data, pdf_filename, str(proposal_id))
        
        github_owner = os.getenv("GITHUB_OWNER", "coolmag")
        github_repo = os.getenv("GITHUB_REPO", "KPbot")
        web_url = f"https://{github_owner}.github.io/{github_repo}/proposals/{proposal_id}.html"
        
        task_send_result.apply_async(args=[chat_id, proposal_id, web_url, pdf_filename], countdown=10)
        
        print(f"✅ [Worker] КП #{proposal_id} сгенерировано. Отправка клиенту через 10 секунд...")
        return True
        
    print(f"❌ [Worker] Ошибка AI-генерации для КП #{proposal_id}")
    return False
