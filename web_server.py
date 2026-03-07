import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import telegram
import asyncio

# --- CONFIGURATION ---
# Загрузка переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# ID менеджера, куда будут приходить уведомления. Должен быть в .env
MANAGER_ID = os.getenv("MANAGER_TELEGRAM_ID")

logger = logging.getLogger(__name__)

# --- INITIALIZATION ---
app = FastAPI()

# Настройка CORS для разрешения запросов с вашего сайта на GitHub Pages
# Укажите реальный домен вашего сайта на GitHub Pages
origins = [
    "https://coolmag.github.io",
    "http://localhost", # Для локальной разработки
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ENDPOINTS ---
@app.post("/api/accept/{proposal_id}")
async def accept_proposal(proposal_id: int):
    """
    API-метод, который вызывается при нажатии кнопки "Принять" на веб-странице.
    Отправляет уведомление менеджеру.
    """
    logger.info(f"Получен запрос на принятие КП #{proposal_id}")

    if not BOT_TOKEN or not MANAGER_ID:
        logger.error("TELEGRAM_BOT_TOKEN или MANAGER_TELEGRAM_ID не установлены!")
        raise HTTPException(status_code=500, detail="Сервер не настроен для отправки уведомлений.")

    try:
        bot = telegram.Bot(token=BOT_TOKEN)
        text = f"🎉 **Сделка принята!**

Клиент принял коммерческое предложение `ID: {proposal_id}`.

Пора действовать! 🔥"
        
        await bot.send_message(
            chat_id=MANAGER_ID,
            text=text,
            parse_mode='Markdown'
        )
        
        logger.info(f"Уведомление о принятии КП #{proposal_id} успешно отправлено менеджеру {MANAGER_ID}")
        return {"status": "ok", "message": "Notification sent"}

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления в Telegram: {e}")
        raise HTTPException(status_code=500, detail="Не удалось отправить уведомление.")

@app.get("/")
def read_root():
    return {"status": "API Server for Smart Proposals is running"}

