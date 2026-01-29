from google import genai
from google.genai import types
import os
import logging
import json
import time
import random

logger = logging.getLogger(__name__)

# Схема остается прежней — она отличная
PROPOSAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "description": "Цепляющий заголовок КП"},
        "executive_summary": {"type": "STRING", "description": "Суть предложения (2-3 предложения)"},
        "client_pain_points": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "3-4 боли клиента"
        },
        "solution_steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "step_name": {"type": "STRING"},
                    "description": {"type": "STRING"}
                }
            },
            "description": "Этапы работы"
        },
        "budget_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "item": {"type": "STRING", "description": "Услуга"},
                    "price": {"type": "STRING", "description": "Цена"},
                    "time": {"type": "STRING", "description": "Срок"}
                }
            }
        },
        "why_us": {"type": "STRING", "description": "Почему мы"},
        "cta": {"type": "STRING", "description": "Призыв к действию"}
    },
    "required": ["title", "executive_summary", "solution_steps", "budget_items", "cta"]
}

def get_proposal_json(prompt: str) -> dict:
    """
    Генерирует JSON через Gemini 1.5 Flash с системой повторных попыток (Retries).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не найден.")
        return _get_fallback_data("Ошибка конфигурации API Key")

    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "Ты — опытный коммерческий директор. Твоя задача — создать структуру КП "
        "в формате JSON. Будь краток, убедителен и используй деловой стиль. "
        "Если цены не указаны, предложи реалистичные рыночные оценки."
    )

    # --- НАСТРОЙКИ СТАБИЛЬНОСТИ ---
    # Используем 1.5-flash — она самая стабильная для Free Tier
    MODEL_NAME = "gemini-1.5-flash" 
    MAX_RETRIES = 3
    BASE_DELAY = 4 # секунды

    for attempt in range(MAX_RETRIES):
        try:
            # logger.info(f"🤖 Запрос к AI (Попытка {attempt+1}/{MAX_RETRIES})...")
            
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=PROPOSAL_SCHEMA,
                    # Температура поменьше для стабильности JSON
                    temperature=0.7, 
                )
            )
            
            if not response.text:
                raise ValueError("Пустой ответ от API")

            data = json.loads(response.text)
            logger.info("✅ JSON успешно сгенерирован.")
            return data

        except Exception as e:
            error_msg = str(e)
            
            # Ловим ошибки лимитов (429)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                # Экспоненциальная задержка: 4с -> 8с -> 16с + случайная добавка
                wait_time = BASE_DELAY * (2 ** attempt) + random.uniform(0.5, 2.0)
                logger.warning(f"⏳ Превышен лимит (429). Жду {wait_time:.1f} сек...")
                time.sleep(wait_time)
            
            # Ловим ошибки перегрузки серверов Google (500, 503)
            elif "500" in error_msg or "503" in error_msg:
                wait_time = 5
                logger.warning(f"⏳ Сервер Google перегружен. Жду {wait_time} сек...")
                time.sleep(wait_time)
                
            else:
                logger.error(f"❌ Непредвиденная ошибка AI: {e}")
                # Если ошибка не в лимитах (например, плохой промпт), нет смысла повторять
                break

    logger.error("❌ Все попытки исчерпаны. Отдаем заглушку.")
    return _get_fallback_data("Сервис перегружен. Попробуйте позже.")

def _get_fallback_data(reason: str) -> dict:
    """Возвращает заглушку, чтобы PDF генератор не ломался."""
    return {
        "title": "Коммерческое Предложение (Черновик)",
        "executive_summary": f"Не удалось сгенерировать полный текст с помощью ИИ. Причина: {reason}",
        "client_pain_points": ["Техническая заминка", "Высокая нагрузка на сеть"],
        "solution_steps": [
            {"step_name": "Связаться с менеджером", "description": "Мы обсудим детали лично."}
        ],
        "budget_items": [
            {"item": "Консультация", "price": "Бесплатно", "time": "Сейчас"}
        ],
        "why_us": "Мы всегда на связи, даже когда роботы устали.",
        "cta": "Напишите нам в ЛС"
    }