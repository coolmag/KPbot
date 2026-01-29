from google import genai
from google.genai import types
import os
import logging
import json
import re
import time
import random

logger = logging.getLogger(__name__)

# Схема ответа, которую мы требуем от ИИ
PROPOSAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "description": "Цепляющий заголовок КП"},
        "executive_summary": {"type": "STRING", "description": "Краткая суть предложения (2-3 предложения)"},
        "client_pain_points": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Список из 3-4 болей клиента, которые мы решаем"
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
                    "item": {"type": "STRING", "description": "Название услуги"},
                    "price": {"type": "STRING", "description": "Стоимость (например '50 000 руб')"},
                    "time": {"type": "STRING", "description": "Срок (например '2 дня')"}
                }
            }
        },
        "why_us": {"type": "STRING", "description": "Блок 'Почему мы'"},
        "cta": {"type": "STRING", "description": "Призыв к действию (Call to Action)"}
    },
    "required": ["title", "executive_summary", "solution_steps", "budget_items", "cta"]
}


def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не найден.")
        return None

    client = genai.Client(api_key=api_key)
    
    system_instruction = (
        "Ты — топовый эксперт по B2B продажам. Твоя цель — составить структуру "
        "убойного Коммерческого Предложения. Пиши уверенно, без воды. "
        "Цены придумывай реалистичные, если не указаны."
    )

    # --- НАЧАЛО ИЗМЕНЕНИЙ: Блок повторных попыток ---
    max_retries = 3
    base_delay = 5 # секунд
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=PROPOSAL_SCHEMA
                )
            )
            
            # Если успех — сразу возвращаем
            data = json.loads(response.text)
            logger.info("✅ JSON от Gemini успешно получен.")
            return data

        except Exception as e:
            # Проверяем, если это ошибка лимитов (429)
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"⚠️ Лимит API (429). Жду {wait_time:.1f} сек... (Попытка {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                # Если ошибка другая (не лимиты) — выходим сразу
                logger.error(f"❌ Критическая ошибка AI: {e}")
                break
    # --- КОНЕЦ ИЗМЕНЕНИЙ ---

    # Если все попытки исчерпаны, возвращаем заглушку
    logger.error("❌ Все попытки исчерпаны. Возвращаю заглушку.")
    return {
        "title": "Сервис перегружен",
        "executive_summary": "Извините, нейросеть сейчас испытывает высокую нагрузку. Попробуйте через минуту.",
        "client_pain_points": ["Лимиты API Google", "Высокая нагрузка"],
        "solution_steps": [],
        "budget_items": [{"item": "Ожидание слота", "price": "0", "time": "∞"}],
        "cta": "Нажмите /start снова"
    }