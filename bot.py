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

# --- СИСТЕМА БЕЗОПАСНОСТИ: БЕЛЫЕ СПИСКИ ID ---
def _parse_ids_from_env(env_var_name: str) -> list[int]:
    """Парсит ID из переменной окружения (строка через запятую)."""
    ids_str = os.getenv(env_var_name, "")
    if not ids_str:
        return []
    try:
        return [int(id.strip()) for id in ids_str.split(',')]
    except ValueError:
        logger.error(f"Ошибка в формате переменной {env_var_name}. ID должны быть числами, разделенными запятой.")
        return []

ALLOWED_CHAT_IDS = _parse_ids_from_env("ALLOWED_CHAT_IDS")
ALLOWED_USER_IDS = _parse_ids_from_env("ALLOWED_USER_IDS")

logger.info(f"Загружены ID разрешенных чатов: {ALLOWED_CHAT_IDS}")
logger.info(f"Загружены ID разрешенных пользователей: {ALLOWED_USER_IDS}")
# --------------------------------------------------------------------

ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)

async def check_chat_access(update: Update):
    """
    Проверяет доступ. Логика:
    - В приватных чатах (ЛС) разрешено только пользователям из белого списка.
    - В групповых чатах разрешено всем, если группа в белом списке.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    # 1. Логика для личных сообщений (ЛС)
    if chat_type == 'private':
        if user_id in ALLOWED_USER_IDS:
            return True
        else:
            logger.warning(f"Отказ в доступе (ЛС). UserID: {user_id}")
            await update.message.reply_text("⛔ Доступ запрещен. Этот бот предназначен для корпоративного использования.")
            return False

    # 2. Логика для групп
    if chat_type in ['group', 'supergroup']:
        if chat_id in ALLOWED_CHAT_IDS:
            return True
        else:
            logger.warning(f"Попытка использования в неавторизованной группе. ChatID: {chat_id}")
            await update.message.reply_text("⛔ Я не могу работать в этом чате. Я являюсь частным ботом KOTEL.MSK.RU.")
            try:
                await update.effective_chat.leave()
            except Exception as e:
                logger.error(f"Не удалось выйти из чата {chat_id}: {e}")
            return False
            
    # 3. На случай других типов чатов (например, каналы)
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