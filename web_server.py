import os
import logging
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types

from database import get_proposal_data, log_event
from celery_worker import task_generate_proposal

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MANAGER_ID = os.getenv("MANAGER_TELEGRAM_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logger = logging.getLogger(__name__)

# --- MODELS ---
class TrackEvent(BaseModel):
    proposal_id: str
    event_type: str
    metadata: dict = None

class Question(BaseModel):
    question: str
    proposal_id: str

# --- INITIALIZATION ---
app = FastAPI()

origins = ["https://coolmag.github.io", "http://localhost", "null"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER FUNCTIONS ---
def notify(text: str):
    """Синхронно отправляет уведомление в Telegram."""
    if not BOT_TOKEN or not MANAGER_ID:
        logger.error("TELEGRAM_BOT_TOKEN или MANAGER_TELEGRAM_ID не установлены!")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": MANAGER_ID, "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Уведомление успешно отправлено: {text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке уведомления в Telegram: {e}")

# --- API ENDPOINTS ---
@app.post("/track")
def track_client_action(event: TrackEvent):
    """Сбор Heatmap и событий"""
    log_event(event.proposal_id, event.event_type, event.metadata)
    
    # AI Co-pilot: уведомляем менеджера о важных шагах
    if event.event_type == "scrolled_80":
        notify(f"🔥 Клиент долистал КП `#{event.proposal_id}` до конца!")
    elif event.event_type == "plan_clicked":
        plan_name = event.metadata.get("plan_name", "")
        notify(f"💰 Клиент кликнул на тариф **{plan_name}** в КП `#{event.proposal_id}`!")
        
    return {"status": "ok"}

@app.post("/ai")
async def ai_chat(q: Question):
    """Умный AI-помощник: Общение + Пересчет КП"""
    log_event(q.proposal_id, "ai_question", {"question": q.question})
    notify(f"💬 Вопрос по КП `#{q.proposal_id}`:
_{q.question}_")
    
    current_kp = get_proposal_data(q.proposal_id)
    
    prompt = f"""
    Ты - AI инженер по продажам. Клиент задал вопрос по коммерческому предложению (ID: {q.proposal_id}).
    Текущие данные КП: {json.dumps(current_kp, ensure_ascii=False)[:500]}...
    Вопрос клиента: "{q.question}"

    ПРАВИЛА:
    1. Если клиент просто задает вопрос (например, "Шумный ли котел?") -> ответь вежливо.
    2. Если клиент просит изменить условия (площадь, другой котел, добавить теплый пол) -> верни команду на пересчет.
    
    Верни СТРОГО JSON:
    {{
        "action": "chat" или "recalculate",
        "reply_text": "твой ответ клиенту",
        "new_task_context": "если action=recalculate, напиши сюда новое ТЗ для генератора (например: Дом 200м2, нужен теплый пол), иначе null"
    }}
    """
    
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = await client.aio.models.generate_content(
            model='gemma-3-27b-it',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        ai_decision = json.loads(response.text)
        
        if ai_decision.get("action") == "recalculate":
            new_task = ai_decision.get("new_task_context")
            if new_task:
                task_generate_proposal.delay(int(q.proposal_id), current_kp.get('client_name', 'Клиент'), new_task)
                log_event(q.proposal_id, "recalculation_triggered", {"new_task": new_task})
                notify(f"🔄 **Клиент запустил пересчет КП #{q.proposal_id}!**
Новое ТЗ: {new_task}")
                
                return {
                    "answer": ai_decision.get("reply_text", "Принял. Пересчитываю...") + " Страница обновится через 15-20 секунд.",
                    "action": "recalculate"
                }
        
        return {"answer": ai_decision.get("reply_text", "Не совсем понял, сейчас позову менеджера."), "action": "chat"}
        
    except Exception as e:
        logger.error(f"AI decision processing error: {e}")
        return {"answer": "Ой, я немного запутался. Менеджер скоро свяжется с вами!", "action": "error"}

@app.get("/")
def read_root():
    return {"status": "Production API Server v5.0 - Interactive AI & Celery Ready"}
