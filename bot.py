import os
import logging
import sys
import asyncio
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# Импорты проекта
from ai_service import get_proposal_text
from pdf_generator import create_proposal_pdf
from utils import ensure_font_exists

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования (важно выводить в stdout для Railway)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)

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
    
    await update.message.reply_text("🤖 Анализирую задачу и пишу текст...")

    # Подготовка промпта
    prompt = (
        f"Исполнитель: {context.user_data['about_you']}\n"
        f"Клиент: {context.user_data['about_client']}\n"
        f"Задача: {context.user_data['task_info']}"
    )

    # 1. Генерация текста (IO-bound, но библиотека синхронная, запускаем в executor)
    # Если библиотека поддерживает async, лучше использовать его.
    # Но для google-generativeai сейчас безопаснее использовать run_in_executor
    loop = asyncio.get_running_loop()
    
    try:
        proposal_text = await loop.run_in_executor(None, get_proposal_text, prompt)
    except Exception as e:
        logger.error(f"Ошибка AI: {e}")
        await update.message.reply_text("Ошибка при генерации текста.")
        return ConversationHandler.END

    await update.message.reply_text("📄 Верстаю PDF документ...")

    # 2. Генерация PDF (CPU-bound, ОБЯЗАТЕЛЬНО выносить в executor)
    try:
        pdf_bytes = await loop.run_in_executor(None, create_proposal_pdf, proposal_text)
        
        if not pdf_bytes:
            raise Exception("PDF файл пустой")

        await update.message.reply_document(
            document=pdf_bytes,
            filename="Commercial_Proposal.pdf",
            caption="✅ Ваше КП готово! Используйте /start для нового."
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
    """Выполняется один раз перед запуском бота."""
    logger.info("⚙️ Проверка системных требований...")
    
    # Проверяем шрифт при старте, чтобы не было сюрпризов в рантайме
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

    # Используем post_init для проверки окружения
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ABOUT_YOU: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_you)],
            ABOUT_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_client)],
            TASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_info)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('cancel', cancel))

    logger.info("🚀 Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()