import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import google.generativeai as genai

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MANAGER_ID = os.getenv("MANAGER_TELEGRAM_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logger = logging.getLogger(__name__)

# --- MODELS ---
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

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

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

async def get_ai_answer(question: str, proposal_id: str) -> str:
    """Асинхронно генерирует ответ на вопрос клиента с помощью AI."""
    if not GOOGLE_API_KEY:
        return "AI-чат временно недоступен: не настроен API-ключ."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Ты — вежливый AI-ассистент по продажам. "
            "Отвечай кратко, по делу и дружелюбно. "
            "Если не знаешь ответ, предложи позвать менеджера.\n\n"
            f"Вопрос клиента по предложению #{proposal_id}: '{question}'"
        )
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Ошибка генерации ответа AI: {e}")
        return "К сожалению, произошла ошибка при обработке вашего вопроса."

# --- API ENDPOINTS ---
@app.post("/ai")
async def ai_chat(q: Question):
    logger.info(f"AI-чат (КП #{q.proposal_id}): '{q.question}'")
    notify(f"💬 Вопрос по КП `#{q.proposal_id}`:\n_{q.question}_")
    answer = await get_ai_answer(q.question, q.proposal_id)
    return {"answer": answer}

@app.get("/view")
def view_proposal(id: str):
    logger.info(f"Отмечен просмотр КП #{id}")
    notify(f"👀 Клиент открыл КП `#{id}`")
    return {"ok": True}

@app.get("/accept")
def accept_proposal(id: str):
    logger.info(f"Получен запрос на принятие КП #{id}")
    notify(f"🔥 **Сделка принята!**\nКлиент принял коммерческое предложение `ID: {id}`.")
    return {"ok": True}

@app.get("/")
def read_root():
    return {"status": "Production API Server v3.0 is running"}

