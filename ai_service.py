import os
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


def get_proposal_text(prompt):
    """Генерирует КП через Google Gemini Pro."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Нет GOOGLE_API_KEY")
        return "Ошибка: нет ключа API."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        request_text = (
            f"Ты — профессиональный помощник. Составь короткое коммерческое предложение "
            f"на основе данных: {prompt}. "
            f"Структура: Приветствие, Суть задачи, Решение, Призыв к действию. "
            f"Не используй Markdown. Пиши просто."
        )

        response = model.generate_content(request_text)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Ошибка Google AI: {e}")
        return (
            "Коммерческое предложение (Черновик)\n\n"
            "Здравствуйте!\n"
            "Спасибо за ваш запрос. Мы готовы взяться за ваш проект.\n"
            "К сожалению, AI-модуль временно недоступен, "
            "но мы свяжемся с вами лично для уточнения."
        )

