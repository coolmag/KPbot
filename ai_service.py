from google import genai
from google.genai import types
import os
import logging
import json
import time
import re

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

def clean_json_response(content: str) -> dict | None:
    try:
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            return json.loads(content[start:end+1])
    except:
        pass
    return None

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return _get_fallback_data("Нет ключа")

    client = genai.Client(api_key=api_key)
    
    # Gemma не поддерживает System Instruction в конфиге, поэтому вшиваем в промпт
    full_prompt_gemma = (
        "Ты — Инженер-сметчик. Составь КП на котельную в формате JSON. "
        "Правила: Язык Русский. Исправляй 'конвективы' -> 'конвекторы'. "
        "Указывай цены в рублях (примерно). "
        "Ответ должен быть ТОЛЬКО JSON объектом по схеме: "
        '{"title": "...", "executive_summary": "...", "client_pain_points": ["..."], '
        '"solution_steps": [{"step_name": "...", "description": "..."}], '
        '"budget_items": [{"item": "...", "price": "...", "time": "..."}], '
        '"why_us": "...", "cta": "..."}\n\n' 
        f"ЗАДАЧА: {prompt}"
    )

    # Список моделей (Gemma - открытая, Gemini - проприетарная)
    TARGET_MODELS = [
        "gemma-3-27b-it", 
        "gemma-2-9b-it",
        "gemini-2.0-flash-exp" # На случай, если лимиты сбросятся
    ]

    for model_name in TARGET_MODELS:
        try:
            logger.info(f"⚡ Пробую модель: {model_name}...")
            
            # Для GEMMA (упрощенный конфиг)
            if "gemma" in model_name:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt_gemma,
                    config=types.GenerateContentConfig(
                        temperature=0.3
                        # Убрали system_instruction, tools и mime_type
                    )
                )
            
            # Для GEMINI (полный фарш, но без конфликта JSON + Search)
            else:
                # Используем поиск, но просим JSON текстом (mime_type удаляем)
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt_gemma, # Тоже используем полный промпт
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )

            if response.text:
                data = clean_json_response(response.text)
                if data and "title" in data:
                    logger.info(f"✅ Успех ({model_name})!")
                    return data
                
        except Exception as e:
            logger.info(f"⚠️ Ошибка {model_name}: {e}")
            if "429" in str(e): time.sleep(2)
            continue

    return _get_fallback_data("Все модели заняты")

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
