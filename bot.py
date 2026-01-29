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

from ai_service import get_proposal_json # <-- Импортируем новую функцию
from pdf_generator import create_proposal_pdf
from utils import ensure_font_exists

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)

# --- Хендлер для логирования всех входящих сообщений ---
async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        logger.info(f"📩 Новое сообщение от {update.message.from_user.first_name}: {update.message.text}")
# -------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🎯 *AI Client Pilot*\n\n"
        "Я помогу составить структуру КП. Начнем!\n\n"
        "📝 *О Вас:* Напишите название вашей компании и чем вы занимаетесь.",
        parse_mode='Markdown'
    )
    return ABOUT_YOU

async def about_you(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['about_you'] = update.message.text
    await update.message.reply_text("👤 *О Клиенте:* Кто ваш клиент? (Ниша, название, проблемы)")
    return ABOUT_CLIENT

async def about_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['about_client'] = update.message.text
    await update.message.reply_text("💼 *Задача:* Что нужно сделать? (Сроки, бюджет, детали)")
    return TASK_INFO

async def task_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['task_info'] = update.message.text
    
    await update.message.reply_text("🤖 Генерирую структуру КП (Data-Driven)...")

    prompt = (
        f"Данные об исполнителе: {context.user_data['about_you']}\n"
        f"Данные о клиенте: {context.user_data['about_client']}\n"
        f"Задача проекта: {context.user_data['task_info']}"
    )

    loop = asyncio.get_running_loop()
    
    # 1. Получаем JSON структуру
    try:
        proposal_data = await loop.run_in_executor(None, get_proposal_json, prompt)
        if not proposal_data:
            raise Exception("AI вернул пустой ответ")
    except Exception as e:
        logger.error(f"Ошибка AI: {e}")
        await update.message.reply_text("Произошла ошибка при обращении к мозгу ИИ.")
        return ConversationHandler.END

    await update.message.reply_text("🎨 Верстаю дизайнерский PDF...")

    # 2. Генерируем PDF по JSON
    try:
        pdf_bytes = await loop.run_in_executor(None, create_proposal_pdf, proposal_data)
        
        if not pdf_bytes:
            raise Exception("PDF файл пустой")

        # Отправляем
        await update.message.reply_document(
            document=pdf_bytes,
            filename=f"KP_{context.user_data.get('about_client', 'Client')[:10]}.pdf",
            caption="🚀 Ваше КП готово! Заряжено на успех."
        )
    except Exception as e:
        logger.error(f"Ошибка отправки PDF: {e}")
        await update.message.reply_text("Не удалось создать PDF файл.")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 Отменено. Нажмите /start.")
    context.user_data.clear()
    return ConversationHandler.END

async def post_init(application: Application) -> None:
    logger.info("⚙️ Проверка системных требований...")
    font = ensure_font_exists()
    if font:
        logger.info(f"✅ Шрифт готов: {font}")
    else:
        logger.warning("⚠️ Шрифт не загружен! Кириллица может не работать.")

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.critical("❌ TELEGRAM_BOT_TOKEN не найден!")
        sys.exit(1)

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # Регистрируем логгер обновлений ПЕРВЫМ, чтобы видеть всё
    application.add_handler(TypeHandler(Update, log_update), group=-1)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ABOUT_YOU: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_you)],
            ABOUT_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_client)],
            TASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_info)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True  # <--- ВАЖНОЕ ИСПРАВЛЕНИЕ: Разрешает перезапуск бота в любой момент
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('cancel', cancel))

    logger.info("🚀 Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()
