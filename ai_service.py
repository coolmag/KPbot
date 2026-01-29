from google import genai
from google.genai import types
import os
import logging
import json
import time
import random

logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ 2026 ---
# Приоритетный список моделей. 1.5 убрали, так как они deprecated.
# Добавили 2.0 и экспериментальные версии (у них часто свои отдельные квоты).
MODEL_PRIORITY = [
    "gemini-2.0-flash",          # Стандарт (быстрая)
    "gemini-2.0-flash-exp",      # Экспериментальная (часто работает, когда основа занята)
    "gemini-2.0-flash-001",      # Версия с фиксацией
    "gemini-2.5-flash",          # Новейшая (если доступна)
]

PROPOSAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "executive_summary": {"type": "STRING"},
        "client_pain_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "solution_steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "step_name": {"type": "STRING"},
                    "description": {"type": "STRING"}
                }
            }
        },
        "budget_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "item": {"type": "STRING"},
                    "price": {"type": "STRING"},
                    "time": {"type": "STRING"}
                }
            }
        },
        "why_us": {"type": "STRING"},
        "cta": {"type": "STRING"}
    },
    "required": ["title", "executive_summary", "solution_steps", "budget_items", "cta"]
}

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не найден.")
        return _get_fallback_data("Нет API ключа")

    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "Ты — опытный коммерческий директор. Составь структуру КП в JSON. "
        "Цены пиши в рублях, сроки реальные. Стиль: уверенный B2B."
    )

    # Пробуем модели по очереди
    for model_name in MODEL_PRIORITY:
        # Для каждой модели делаем до 3 попыток (чтобы пробить 429)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # logger.info(f"⚡ Запрос к {model_name} (Попытка {attempt+1}/{max_retries})...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=PROPOSAL_SCHEMA,
                        temperature=0.7,
                    )
                )

                if response.text:
                    logger.info(f"✅ Успех! Сработала {model_name}")
                    return json.loads(response.text)

            except Exception as e:
                error_str = str(e)
                
                # Если 404 (Модель не найдена) -> Сразу следующая модель
                if "404" in error_str or "NOT_FOUND" in error_str:
                    logger.warning(f"🚫 {model_name} не найдена (404).")
                    break # Break inner loop -> Next model
                
                # Если 429 (Лимиты) -> Ждем и пробуем эту же модель снова
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = 4 + (attempt * 2) + random.uniform(0, 2)
                    logger.warning(f"⏳ Лимиты на {model_name}. Жду {wait_time:.1f} сек...")
                    time.sleep(wait_time)
                    continue # Retry same model
                
                # Другие ошибки -> Логируем и следующая модель
                logger.error(f"⚠️ Ошибка {model_name}: {error_str}")
                break 

    logger.error("❌ Все модели перегружены или недоступны.")
    return _get_fallback_data("Серверы перегружены")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Коммерческое Предложение (Офлайн)",
        "executive_summary": f"К сожалению, ИИ сейчас перегружен ({reason}). Мы подготовим КП вручную.",
        "client_pain_points": ["Высокая загрузка серверов"],
        "solution_steps": [],
        "budget_items": [{"item": "Расчет менеджером", "price": "По запросу", "time": "В рабочее время"}],
        "why_us": "Мы надежнее нейросетей.",
        "cta": "Свяжитесь с нами"
    }