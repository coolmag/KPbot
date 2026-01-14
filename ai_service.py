import os
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Кэш для хранения имени найденной модели, чтобы не делать лишних запросов
_cached_model_name: str | None = None

def _find_best_generative_model(client: genai.Client) -> str | None:
    """
    Находит наиболее подходящую модель для генерации текста,
    делая один запрос к API и кэшируя результат.
    Приоритет отдается 'pro' моделям.
    """
    global _cached_model_name
    if _cached_model_name:
        return _cached_model_name

    logger.info("🔍 Поиск доступных моделей Gemini...")
    pro_models = []
    other_models = []

    try:
        for m in client.models.list():
            if "generateContent" in m.supported_generation_methods:
                if 'pro' in m.name:
                    pro_models.append(m.name)
                else:
                    other_models.append(m.name)
    except Exception as e:
        logger.error(f"❌ Не удалось получить список моделей: {e}", exc_info=True)
        return None

    if pro_models:
        # Сортируем, чтобы попытаться использовать последнюю версию (если есть нумерация)
        _cached_model_name = sorted(pro_models, reverse=True)[0]
        logger.info(f"✅ Выбрана 'pro' модель: {_cached_model_name}")
    elif other_models:
        _cached_model_name = sorted(other_models, reverse=True)[0]
        logger.info(f"✅ Выбрана 'flash'/'lite' модель: {_cached_model_name}")
    else:
        logger.error("❌ Не найдено ни одной подходящей модели с поддержкой 'generateContent'.")
        return None
    
    return _cached_model_name

def get_proposal_text(prompt: str) -> str:
    """
    Генерирует КП, динамически выбирая лучшую доступную модель.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не установлен.")
        return "Ошибка: Отсутствует API ключ Google."

    try:
        client = genai.Client(api_key=api_key)
        
        model_name = _find_best_generative_model(client)
        if not model_name:
            raise Exception("Подходящая модель Gemini не найдена.")

        full_prompt = (
            f"Ты — профессиональный бизнес-ассистент. Составь коммерческое предложение "
            f"на основе данных: {prompt}. "
            f"Структура: Приветствие, Понимание задачи, Предлагаемое решение, Сроки и стоимость (примерные), Призыв к действию. "
            f"Форматирование: Не используй Markdown (жирный, курсив, заголовки #), "
            f"пиши простым текстом, разделяя смысловые блоки пустыми строками."
        )

        response = client.models.generate_content(
            model=model_name,
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