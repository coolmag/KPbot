from google import genai
from google.genai import types
import os
import logging
import json
import time
import re

logger = logging.getLogger(__name__)

# Схема для JSON Mode (Gemini это любит)
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
    """
    Генерация через Google Gemini 2.5 Flash с Google Search.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не найден!")
        return _get_fallback_data("Нет API ключа")

    client = genai.Client(api_key=api_key)
    
    # Промпт инженера
    system_instruction = (
        "Ты — Главный инженер компании KOTEL.MSK.RU (стаж 30 лет). "
        "Ты составляешь сметы для котельных. "
        "Твои правила:\n"
        "1. Пиши только на русском. Используй профессиональные термины (гидрострелка, бойлер косвенного нагрева).\n"
        "2. Исправляй ошибки клиента ('конвективы' -> 'конвекторы').\n"
        "3. В смете ОБЯЗАТЕЛЬНО указывай цены в рублях (примерно, рыночные). Не оставляй поля пустыми!\n"
    )

    # Список моделей (от новой к старой)
    # Используем названия без префикса models/ для нового SDK, если он сам подставляет
    MODELS = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]

    for model_name in MODELS:
        try:
            logger.info(f"⚡ Пробую Google: {model_name}...")
            
            # Конфигурация с ПОИСКОМ (Google Search Grounding)
            # Внимание: Tools configuration может отличаться в разных версиях SDK.
            # Если tool google_search_retrieval недоступен на Free Tier, он просто проигнорируется или выдаст ошибку,
            # тогда мы переключимся на обычный режим.
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=PROPOSAL_SCHEMA,
                    temperature=0.4,
                    # Включаем поиск (если доступно)
                    tools=[types.Tool(
                        google_search=types.GoogleSearch() # Встроенный гуглинг!
                    )]
                )
            )
            
            if response.text:
                logger.info(f"✅ Успех ({model_name})!")
                return json.loads(response.text)
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка {model_name}: {e}")
            # Если ошибка 429 (лимиты), ждем
            if "429" in str(e):
                time.sleep(5)
            continue

    return _get_fallback_data("Google API недоступен")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Смета (Расчет менеджером)",
        "executive_summary": f"Система AI перегружена ({reason}). Свяжитесь с нами.",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "Ручной расчет", "price": "По запросу", "time": "-"}],
        "why_us": "KOTEL.MSK.RU",
        "cta": "Позвонить"
    }