from google import genai
from google.genai import types
import os
import logging
import json
import re

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
    """
    Генерирует структурированные данные для КП.
    Возвращает словарь (dict).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не найден.")
        return None

    client = genai.Client(api_key=api_key)
    
    # Системный промпт для роли "Архитектора продаж"
    system_instruction = (
        "Ты — топовый эксперт по B2B продажам. Твоя цель — составить структуру "
        "убойного Коммерческого Предложения. Пиши уверенно, без воды. "
        "Используй маркетинговые триггеры. Цены придумывай реалистичные, если не указаны."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Используем быструю и умную модель
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", # ВАЖНО: Форсируем JSON
                response_schema=PROPOSAL_SCHEMA
            )
        )
        
        raw_json = response.text
        data = json.loads(raw_json)
        logger.info("✅ JSON от Gemini успешно получен и распарсен.")
        return data

    except Exception as e:
        logger.error(f"Ошибка генерации JSON: {e}")
        # Возвращаем заглушку, чтобы бот не падал
        return {
            "title": "Ошибка генерации",
            "executive_summary": "Не удалось получить ответ от нейросети.",
            "client_pain_points": ["Ошибка доступа", "Сбой API"],
            "solution_steps": [],
            "budget_items": [{"item": "Анализ ошибки", "price": "0", "time": "1 мин"}],
            "cta": "Попробуйте позже"
        }
