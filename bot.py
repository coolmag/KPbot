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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- ЧИТАЕМ СПИСОК РАЗРЕШЕННЫХ ГРУПП ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
def get_allowed_chats():
    allowed_chats_str = os.getenv("ALLOWED_CHAT_IDS", "")
    if not allowed_chats_str:
        logger.warning("Переменная ALLOWED_CHAT_IDS не задана. Бот будет работать только в личных сообщениях.")
        return []
    try:
        # Преобразуем строку "id1,id2,id3" в список чисел [id1, id2, id3]
        return [int(chat_id.strip()) for chat_id in allowed_chats_str.split(',')]
    except ValueError:
        logger.error("Ошибка в формате ALLOWED_CHAT_IDS. ID должны быть числами, разделенными запятой.")
        return []

ALLOWED_CHATS = get_allowed_chats()
# --------------------------------------------------------------------

ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)

async def check_chat_access(update: Update):
    """Проверяет, можно ли работать в этом чате"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    # В личке (PRIVATE) работаем всегда
    if chat_type == 'private':
        return True
        
    # В группах - только если ID в белом списке
    if chat_id in ALLOWED_CHATS:
        return True
        
    # Если группа чужая
    await update.message.reply_text("⛔ Извините, я корпоративный бот KOTEL.MSK.RU и работаю только в авторизованных чатах.")
    try:
        await update.effective_chat.leave() # Бот удаляется из группы
    except Exception as e:
        logger.error(f"Не удалось выйти из чата: {e}")
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # 1. Проверка доступа
    if not await check_chat_access(update):
        return ConversationHandler.END

    user = update.effective_user
    logger.info(f"🚀 /start от {user.id} в чате {update.effective_chat.id}")
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я AI-инженер KOTEL.MSK.RU.\n"
        "1️⃣ Напишите название вашей компании и чем занимаетесь.",
        reply_markup=ForceReply(selective=True)
    )
    return ABOUT_YOU

async def about_you(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # В хендлерах внутри диалога тоже можно проверять, но обычно start достаточно.
    context.user_data['about_you'] = update.message.text
    await update.message.reply_text(
        "2️⃣ Кто ваш клиент? (Ниша, проблемы)",
        reply_markup=ForceReply(selective=True)
    )
    return ABOUT_CLIENT

async def about_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['about_client'] = update.message.text
    await update.message.reply_text(
        "3️⃣ Опишите задачу (ТЗ, оборудование, бюджет).",
        reply_markup=ForceReply(selective=True)
    )
    return TASK_INFO

async def task_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['task_info'] = update.message.text
    msg = await update.message.reply_text("⏳ Проектирую решение...")

    prompt = (
        f"Исполнитель: {context.user_data.get('about_you')}\n"
        f"Клиент: {context.user_data.get('about_client')}\n"
        f"Задача: {context.user_data.get('task_info')}"
    )

    loop = asyncio.get_running_loop()
    try:
        proposal_data = await loop.run_in_executor(None, get_proposal_json, prompt)
        if not proposal_data or "title" not in proposal_data:
            await msg.edit_text("❌ Ошибка генерации.")
            return ConversationHandler.END

        await msg.edit_text("📄 Формирую PDF...")
        pdf_bytes = await loop.run_in_executor(None, create_proposal_pdf, proposal_data)
        
        if pdf_bytes:
            filename = f"KP_{context.user_data.get('about_client', 'Client')[:10]}.pdf"
            await update.message.reply_document(document=pdf_bytes, filename=filename, caption="✅ Готово!")
        else:
            await msg.edit_text("❌ Ошибка PDF.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text("⚠️ Сбой.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 Отмена.")
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None: 
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN: sys.exit("No token")

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ABOUT_YOU: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_you)],
            ABOUT_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_client)],
            TASK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_info)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,
        per_chat=False 
    )

    application.add_handler(conv_handler)
    logger.info("🚀 Бот запущен (Secure Mode)")
    application.run_polling()

if __name__ == '__main__':
    main()