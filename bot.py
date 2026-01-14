import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла В САМОМ НАЧАЛЕ
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)

# Импортируем наши модули
from ai_service import get_proposal_text
from pdf_generator import create_proposal_pdf

# Настройка логирования для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для FSM
ABOUT_YOU, ABOUT_CLIENT, TASK_INFO = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "🎯 *AI Client Pilot* — Генератор коммерческих предложений\n\n"
        "Чтобы составить качественное КП, мне нужно узнать несколько деталей.\n\n"
        "📝 *Кто вы?* (Ваша компания/специализация, чем занимаетесь)",
        parse_mode='Markdown'
    )
    return ABOUT_YOU


async def about_you(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сбор информации о пользователе."""
    context.user_data['about_you'] = update.message.text
    await update.message.reply_text(
        "👤 *Кто ваш клиент?* (Название компании, сфера деятельности, размер)",
        parse_mode='Markdown'
    )
    return ABOUT_CLIENT
    

async def about_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сбор информации о клиенте."""
    context.user_data['about_client'] = update.message.text
    await update.message.reply_text(
        "💼 *Суть задачи* (Что нужно сделать, какие сроки, бюджет если известен)",
        parse_mode='Markdown'
    )
    return TASK_INFO


async def task_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сбор информации о задаче и генерация КП."""
    context.user_data['task_info'] = update.message.text

    # Формируем промпт из собранных данных
    prompt = f"""
Кто исполнитель: {context.user_data['about_you']}
Кто клиент: {context.user_data['about_client']}
Задача: {context.user_data['task_info']}
"""
    await update.message.reply_text("🤖 Думаю над коммерческим предложением...")

    # Генерируем КП
    try:
        proposal_text = get_proposal_text(prompt)
        if "Ошибка" in proposal_text or "Connection error" in proposal_text:
            await update.message.reply_text(
                "⚠️ Временные проблемы с AI. Вот шаблон КП:\n\n"
                "## Коммерческое предложение\n\n"
                f"**Задача:** {context.user_data['task_info']}\n\n"
                "## Этапы работы:\n"
                "1. Анализ требований\n"
                "2. Разработка\n"
                "3. Тестирование\n\n"
                "## Сроки: [Уточняются]\n"
                "## Стоимость: [Уточняется]\n\n"
                "Готов обсудить детали."
            )
            return ConversationHandler.END
            
        proposal_text_pdf = proposal_text.replace('\n', '<br/>')
    except Exception as e:
        logger.error(f"AI error: {e}")
        await update.message.reply_text(f"Ошибка AI: {e}")
        return ConversationHandler.END

    await update.message.reply_text("📄 Создаю PDF...")

    try:
        pdf_bytes = create_proposal_pdf(proposal_text_pdf)
        await update.message.reply_document(
            document=pdf_bytes,
            filename="Commercial_Proposal.pdf",
            caption="✅ Ваше КП готово!\n\nХотите создать ещё одно? Нажмите /start"
        )
    except Exception as e:
        logger.error(f"PDF error: {e}")
        await update.message.reply_text(f"Ошибка создания PDF: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога."""
    await update.message.reply_text("Отменено. Нажмите /start для начала.")
    context.user_data.clear()
    return ConversationHandler.END





def main() -> None:
    """Основная функция для запуска бота."""
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("Ошибка: Токен TELEGRAM_BOT_TOKEN не найден. Проверьте ваш .env файл.")
        return

    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # ConversationHandler для сбора данных в 3 этапа
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            # Разрешаем /start в группах
            CommandHandler('start', start, filters=filters.ALL)
        ],
        states={
            ABOUT_YOU: [
                MessageHandler(filters.ALL & ~filters.COMMAND, about_you)
            ],
            ABOUT_CLIENT: [
                MessageHandler(filters.ALL & ~filters.COMMAND, about_client)
            ],
            TASK_INFO: [
                MessageHandler(filters.ALL & ~filters.COMMAND, task_info)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('cancel', cancel))

    logger.info("Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()
