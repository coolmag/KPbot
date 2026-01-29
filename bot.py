import os
import logging
import sys
import asyncio
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, TypeHandler
)

from ai_service import get_proposal_json
from pdf_generator import create_proposal_pdf
from utils import ensure_font_exists

load_dotenv()

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Состояния диалога
ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)

# --- Хендлер для отладки (Видит ли бот сообщения?) ---
async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        chat_type = update.message.chat.type
        user = update.message.from_user.first_name
        text = update.message.text
        logger.info(f"📩 [{chat_type}] {user}: {text}")
# -------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"🚀 /start нажат юзером {user.id}")
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я AI-архитектор коммерческих предложений.\n"
        "Давайте создадим мощное КП.\n\n"
        "🏢 **Шаг 1. О Вас**\n"
        "Напишите название вашей компании и чем занимаетесь.\n"
        "*(Пример: СтройМонтаж, строим котельные под ключ)*",
        parse_mode='Markdown'
    )
    return ABOUT_YOU

async def about_you(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['about_you'] = update.message.text
    await update.message.reply_text(
        "👤 **Шаг 2. О Клиенте**\n"
        "Кто ваш клиент? Какие у него проблемы?\n"
        "*(Пример: Частный дом 200м2, жалуются на холод, старый котел сломался)*",
        parse_mode='Markdown'
    )
    return ABOUT_CLIENT

async def about_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['about_client'] = update.message.text
    await update.message.reply_text(
        "💼 **Шаг 3. Задача (ТЗ)**\n"
        "Что нужно сделать? Оборудование, сроки, бюджет?\n"
        "*(Пример: Монтаж Viessmann 60кВт, бойлер, 5 контуров, бюджет 500к)*",
        parse_mode='Markdown'
    )
    return TASK_INFO

async def task_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['task_info'] = update.message.text
    
    status_msg = await update.message.reply_text("🧠 **Анализирую задачу...**\n(Ищу цены, подбираю оборудование)")

    # Формируем промпт
    prompt = (
        f"Исполнитель: {context.user_data.get('about_you')}\n"
        f"Клиент: {context.user_data.get('about_client')}\n"
        f"Задача: {context.user_data.get('task_info')}"
    )

    loop = asyncio.get_running_loop()
    
    try:
        # 1. Генерация JSON (AI + Поиск)
        proposal_data = await loop.run_in_executor(None, get_proposal_json, prompt)
        
        if not proposal_data or "title" not in proposal_data:
            await status_msg.edit_text("❌ ИИ не смог составить КП. Попробуйте уточнить задачу.")
            return ConversationHandler.END

        await status_msg.edit_text("🎨 **Верстаю PDF (Luxury Style)...**")

        # 2. Генерация PDF
        pdf_bytes = await loop.run_in_executor(None, create_proposal_pdf, proposal_data)
        
        if not pdf_bytes:
            raise Exception("Пустой PDF файл")

        # Отправка
        filename = f"KP_{context.user_data.get('about_client', 'Client')[:10]}.pdf"
        await update.message.reply_document(
            document=pdf_bytes,
            filename=filename,
            caption="✅ **Ваше КП готово!**\n\nУдачи в сделке! Нажмите /start для нового."
        )

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 Диалог сброшен. Жмите /start.")
    context.user_data.clear()
    return ConversationHandler.END

async def post_init(application: Application) -> None:
    logger.info("⚙️ Проверка шрифтов...")
    ensure_font_exists()

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.critical("❌ Токен не найден!")
        sys.exit(1)

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # Логгер (чтобы видеть, что происходит в группах)
    application.add_handler(TypeHandler(Update, log_update), group=-1)

    # Основной диалог
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # Разрешаем текст И команды (кроме /cancel), чтобы в группах бот не тупил
            ABOUT_YOU: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_you)],
            ABOUT_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_client)],
            TASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_info)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        # ВАЖНО: name нужен для сохранения стейта, persistent=False (в памяти)
        name="kp_conversation",
        persistent=False
    )

    application.add_handler(conv_handler)
    
    logger.info("🚀 Бот запущен (Group Mode Ready)")
    application.run_polling()

if __name__ == '__main__':
    main()