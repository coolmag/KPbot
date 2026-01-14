import os
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

def get_proposal_text(prompt: str) -> str:
    """
    Генерирует КП через Google Gemini (Modern SDK). 
    Использует стабильную модель gemini-1.5-pro.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не установлен.")
        return "Ошибка: Отсутствует API ключ Google."

    try:
        client = genai.Client(api_key=api_key)
        
        full_prompt = (
            f"Ты — профессиональный бизнес-ассистент. Составь коммерческое предложение "
            f"на основе данных: {prompt}. "
            f"Структура: Приветствие, Понимание задачи, Предлагаемое решение, Сроки и стоимость (примерные), Призыв к действию. "
            f"Форматирование: Не используй Markdown (жирный, курсив, заголовки #), "
            f"пиши простым текстом, разделяя смысловые блоки пустыми строками."
        )

        # FIX: Используем gemini-1.5-pro (Verified Stable) вместо flash
        response = client.models.generate_content(
            model="gemini-1.5-pro", 
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        
        if not response.text:
            return "AI вернул пустой ответ."
            
        return response.text.strip()

    except Exception as e:
        logger.error(f"❌ Ошибка Google GenAI SDK: {e}", exc_info=True)
        return (
            "Коммерческое предложение (Черновик)\n\n"
            "К сожалению, сервис генерации временно недоступен. "
            "Мы получили ваши вводные данные и свяжемся с вами лично."
        )