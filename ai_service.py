from openai import OpenAI
import os
import logging
import json
import time
import random

logger = logging.getLogger(__name__)

# Список БЕСПЛАТНЫХ моделей на OpenRouter (сортировка по крутости)
# :free в конце названия обязательно для OpenRouter
FREE_MODELS = [
    "google/gemini-2.0-flash-exp:free",      # Google (Быстрый)
    "meta-llama/llama-3.3-70b-instruct:free", # Meta (Мощный)
    "deepseek/deepseek-r1:free",             # DeepSeek (Умный)
    "mistralai/mistral-7b-instruct:free",    # Mistral (Запасной)
]

# Схема для JSON Mode (работает лучше всего с Llama и Gemini)
PROPOSAL_SCHEMA = {
    "type": "json_object", # Стандарт OpenAI
}
def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    # Если забыли ключ OpenRouter, пробуем старый Google (на всякий случай)
    if not api_key:
        logger.error("❌ OPENROUTER_API_KEY не найден!")
        return _get_fallback_data("Нет ключа API")

    # Подключаемся к OpenRouter как к OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    system_instruction = (
        "Ты — профессиональный составитель Коммерческих Предложений (B2B). "
        "Твоя задача — вернуть СТРОГИЙ JSON. Никакого маркдауна (```json), только чистый JSON. "
        "Структура JSON должна быть такой:\n"
        "{\n"
        '  "title": "Заголовок",\n'
        '  "executive_summary": "Суть предложения",\n'
        '  "client_pain_points": ["Боли клиента 1", "Боли клиента 2"],\n'
        '  "solution_steps": [{"step_name": "Этап 1", "description": "Описание"}],\n'
        '  "budget_items": [{"item": "Услуга", "price": "Цена", "time": "Срок"}],\n'
        '  "why_us": "Почему мы",\n'
        '  "cta": "Призыв к действию"\n'
        "}\n"
        "Цены пиши в рублях. Будь убедителен."
    )

    # Перебор моделей
    for model in FREE_MODELS:
        try:
            # logger.info(f"🔄 Пробую модель: {model}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}, # Форсируем JSON
                temperature=0.7,
                # OpenRouter требует эти заголовки для бесплатных лимитов
                extra_headers={
                    "HTTP-Referer": "https://telegram.me/YourBot", 
                    "X-Title": "Proposal Bot",
                }
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Пустой ответ")

            # Иногда модели любят добавить ```json в начало, чистим
            cleaned_json = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(cleaned_json)
            
            # Проверка, что JSON валидный (есть нужные поля)
            if "title" not in data or "budget_items" not in data:
                raise ValueError("Некорректная структура JSON")

            logger.info(f"✅ Успех! Сработала {model}")
            return data

        except Exception as e:
            logger.warning(f"⚠️ Ошибка {model}: {e}")
            time.sleep(1) # Небольшая пауза перед следующей моделью
            continue

    logger.error("❌ Все модели OpenRouter недоступны.")
    return _get_fallback_data("Сервисы перегружены")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "КП (Офлайн режим)",
        "executive_summary": f"ИИ временно недоступен ({reason}). Менеджер свяжется с вами.",
        "client_pain_points": ["Ошибка сети"],
        "solution_steps": [],
        "budget_items": [{"item": "Расчет вручную", "price": "-", "time": "-"}],
        "why_us": "Мы надежнее интернета.",
        "cta": "Позвоните нам"
    }
