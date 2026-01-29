from google import genai
from google.genai import types
import os
import logging
import json
import time

logger = logging.getLogger(__name__)

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
    "required": ["title", "executive_summary", "budget_items", "cta"]
}

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return _get_fallback_data("Нет ключа")

    client = genai.Client(api_key=api_key)
    
    # ИСПОЛЬЗУЕМ GEMMA 3 (у неё лимит 14к запросов!)
    # Пробуем разные варианты написания, так как SDK может быть капризным
    TARGET_MODELS = [
        "gemma-3-27b-it", # Обычно так называется Instruct версия
        "gemma-3-27b",
        "models/gemma-3-27b-it",
        "gemini-2.5-flash" # Запасной, если Gemma недоступна через API (иногда она local-only)
    ]

    system_instruction = (
        "Ты — Инженер-сметчик. Составь КП на котельную. "
        "Язык: Русский. Исправляй ошибки ('конвективы' -> 'конвекторы'). "
        "Цены: Указывай реальные рыночные цены в рублях (примерно). "
        "Не оставляй поля пустыми."
    )

    for model_name in TARGET_MODELS:
        try:
            logger.info(f"⚡ Пробую модель: {model_name}...")
            
            # Gemma 3 может не поддерживать tools (поиск), поэтому пробуем БЕЗ поиска сначала
            # Или включаем поиск только для Gemini
            tools = []
            if "gemini" in model_name:
                tools = [types.Tool(google_search=types.GoogleSearch())]

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=PROPOSAL_SCHEMA,
                    temperature=0.3,
                    tools=tools
                )
            )
            
            if response.text:
                logger.info(f"✅ Успех ({model_name})!")
                return json.loads(response.text)
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка {model_name}: {e}")
            if "429" in str(e): # Если лимиты
                continue 
            if "404" in str(e): # Если модель не найдена
                continue

    return _get_fallback_data("Лимиты исчерпаны")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "КП (Требуется оператор)",
        "executive_summary": f"Все AI модели заняты ({reason}).",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "-", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }