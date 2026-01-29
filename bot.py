import os
import logging
import sys
import asyncio
from dotenv import load_dotenv

from telegram import Update, ForceReply
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

from ai_service import get_proposal_json
from pdf_generator import create_proposal_pdf
from utils import ensure_font_exists

load_dotenv()

# Включаем подробный логгинг
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)

# --- DEBUG HANDLER ---
async def debug_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Этот хендлер ловит ВСЁ в группах и пишет в лог"""
    if update.message:
        chat = update.message.chat
        user = update.message.from_user
        text = update.message.text
        logger.info(f"👀 БОТ ВИДИТ СООБЩЕНИЕ: Chat={chat.title}({chat.id}), User={user.first_name}, Text='{text}'")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"🚀 /start вызван в чате {update.effective_chat.id}")
    await update.message.reply_text(
        "👋 Привет! Я AI-архитектор КП.\n\n"
        "1️⃣ Напишите название вашей компании и чем занимаетесь.",
        # ForceReply заставляет Telegram выделить сообщение бота как "ответ",
        # это помогает боту "слышать" следующий ответ пользователя в группах.
        reply_markup=ForceReply(selective=True) 
    )
    return ABOUT_YOU

async def about_you(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"📝 Получено ABOUT_YOU: {update.message.text}")
    context.user_data['about_you'] = update.message.text
    await update.message.reply_text(
        "2️⃣ Кто ваш клиент? (Ниша, проблемы)",
        reply_markup=ForceReply(selective=True)
    )
    return ABOUT_CLIENT

async def about_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"📝 Получено ABOUT_CLIENT: {update.message.text}")
    context.user_data['about_client'] = update.message.text
    await update.message.reply_text(
        "3️⃣ Опишите задачу (ТЗ, оборудование, бюджет).",
        reply_markup=ForceReply(selective=True)
    )
    return TASK_INFO

async def task_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"📝 Получено TASK_INFO: {update.message.text}")
    context.user_data['task_info'] = update.message.text
    
    msg = await update.message.reply_text("⏳ Думаю... (Ищу цены, проектирую)")

    prompt = (
        f"Исполнитель: {context.user_data.get('about_you')}\n"
        f"Клиент: {context.user_data.get('about_client')}\n"
        f"Задача: {context.user_data.get('task_info')}"
    )

    loop = asyncio.get_running_loop()
    try:
        proposal_data = await loop.run_in_executor(None, get_proposal_json, prompt)
        
        if not proposal_data or "title" not in proposal_data:
            await msg.edit_text("❌ Ошибка ИИ. Попробуйте еще раз.")
            return ConversationHandler.END

        await msg.edit_text("📄 Верстаю PDF...")
        pdf_bytes = await loop.run_in_executor(None, create_proposal_pdf, proposal_data)
        
        if pdf_bytes:
            filename = f"KP_{context.user_data.get('about_client', 'Client')[:10]}.pdf"
            await update.message.reply_document(
                document=pdf_bytes,
                filename=filename,
                caption="✅ Готово!"
            )
        else:
            await msg.edit_text("❌ Ошибка PDF.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text("⚠️ Сбой системы.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 Отмена.")
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        sys.exit("No token")

    application = Application.builder().token(TOKEN).build()

    # 1. Сначала добавляем Debug Handler, чтобы видеть ВСЁ
    application.add_handler(MessageHandler(filters.ALL, debug_group_messages), group=-1)

    # 2. Основной диалог
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # В группах бот часто видит текст как REPLY. Добавляем фильтр REPLY.
            ABOUT_YOU: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_you)],
            ABOUT_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_client)],
            TASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_info)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True, # ВАЖНО: Ведем диалог с конкретным юзером, даже в группе
        per_chat=False 
    )

    application.add_handler(conv_handler)
    
    logger.info("🚀 Бот запущен (Debug Mode)")
    application.run_polling()

if __name__ == '__main__':
    main()
