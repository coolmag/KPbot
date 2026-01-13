import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла В САМОМ НАЧАЛЕ
load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Импортируем наши модули
from ai_service import get_proposal_text
from pdf_generator import create_proposal_pdf

# Настройка логирования для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Здравствуйте! Я ваш AI-ассистент для создания коммерческих предложений.\n\n"
        "Просто отправьте мне краткое описание проекта, и я подготовлю для вас PDF-файл с предложением."
    )


async def generate_proposal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерирует КП на основе сообщения пользователя."""
    # --- НАДЕЖНОЕ ИЗВЛЕЧЕНИЕ СООБЩЕНИЯ ---
    message = update.message or update.edited_message or update.channel_post or update.edited_channel_post
    if not message or not message.text:
        logger.warning(f"Handler triggered for an update with no message text: {update}")
        return
    # --- КОНЕЦ БЛОКА ИЗВЛЕЧЕНИЯ ---

    user_prompt = message.text
    chat_id = message.chat_id
    
    await context.bot.send_message(chat_id, "Принял. Думаю над предложением... 🤖")

    # 1. Получаем текст от AI
    try:
        proposal_text = get_proposal_text(user_prompt)
        # Заменяем переносы строк для корректного отображения в PDF
        proposal_text_pdf = proposal_text.replace('\n', '<br/>')
    except Exception as e:
        logger.error(f"Ошибка в AI сервисе: {e}")
        await context.bot.send_message(chat_id, f"Произошла ошибка при генерации текста: {e}")
        return

    await context.bot.send_message(chat_id, "Текст готов. Создаю PDF... 📄")

    # 2. Создаем PDF
    try:
        pdf_bytes = create_proposal_pdf(proposal_text_pdf)
    except Exception as e:
        logger.error(f"Ошибка в PDF генераторе: {e}")
        await context.bot.send_message(chat_id, f"Произошла ошибка при создании PDF: {e}")
        return

    # 3. Отправляем PDF пользователю
    await context.bot.send_document(
        chat_id=chat_id,
        document=pdf_bytes,
        filename="Commercial_Proposal.pdf",
        caption="Ваше коммерческое предложение готово!"
    )
    
    await context.bot.send_message(
        chat_id, 
        "Вы можете отправить описание следующего проекта."
    )


def main() -> None:
    """Основная функция для запуска бота."""
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("Ошибка: Токен TELEGRAM_BOT_TOKEN не найден. Проверьте ваш .env файл.")
        return

    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_proposal))

    logger.info("Бот запускается...")
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
