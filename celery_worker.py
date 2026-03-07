# celery_worker.py
import os
from celery import Celery
from ai_service import get_smart_proposal
from web_generator import generate_page
from database import update_proposal_with_data

# Подключаемся к Redis (по умолчанию локальный)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery('tasks', broker=redis_url)

@celery_app.task
def task_generate_proposal(proposal_id: int, client: str, task: str):
    """Фоновая задача: AI-Генерация + HTML + Загрузка на GitHub"""
    print(f"🔄 [Worker] Начинаю генерацию для КП #{proposal_id}")
    
    # 1. Запрашиваем Gemma 3
    proposal_data = get_smart_proposal(task)
    
    if proposal_data:
        # 2. Сохраняем JSON в БД
        update_proposal_with_data(proposal_id, proposal_data)
        
        # 3. Генерируем HTML и заливаем на GitHub Pages
        generate_page(proposal_id, client, task, proposal_data)
        print(f"✅ [Worker] КП #{proposal_id} успешно создано и выгружено!")
        return True
    
    print(f"❌ [Worker] Ошибка AI-генерации для КП #{proposal_id}")
    return False

# Запуск воркера в терминале:
# celery -A celery_worker.celery_app worker --loglevel=info
