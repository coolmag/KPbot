from google import genai
from google.genai import types
import os
import logging
import json
import time
import random

logger = logging.getLogger(__name__)

# Список моделей: от самой быстрой/бесплатной к более мощным/старым.
# Бот будет пробовать их по очереди, пока одна не сработает.
MODEL_CHAIN = [
    "gemini-1.5-flash",          # Основная (быстрая, дешевая)
    "gemini-1.5-flash-001",      # Стабильная версия
    "gemini-1.5-flash-002",      # Новая стабильная
    "gemini-1.5-pro",            # Если Flash лежит, берем Pro
    "gemini-2.0-flash-exp",      # Экспериментальная (часто бесплатная)
    "gemini-pro"                 # Старая добрая классика (fallback)
]

# Схема ответа (JSON)
PROPOSAL_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "description": "Заголовок КП"},
        "executive_summary": {"type": "STRING", "description": "Суть (2-3 предл.)"},
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
            "description": "Этапы"
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
        "Ты — бизнес-аналитик. Составь структуру КП в JSON. "
        "Будь краток. Цены предлагай рыночные (в рублях)."
    )

    last_error = None

    # --- ЦИКЛ ПО МОДЕЛЯМ ---
    for model_name in MODEL_CHAIN:
        logger.info(f"🔄 Пробую модель: {model_name}")
        
        # --- ЦИКЛ ПОВТОРНЫХ ПОПЫТОК (Retries) для одной модели ---
        # Делаем 2 попытки на модель, чтобы не висеть вечность
        for attempt in range(2): 
            try:
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
                
                if not response.text:
                    raise ValueError("Пустой ответ")

                data = json.loads(response.text)
                logger.info(f"✅ Успех! Сработала модель: {model_name}")
                return data

            except Exception as e:
                error_msg = str(e)
                last_error = e
                
                # Анализируем ошибку
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    # Если лимиты - ждем чуть-чуть и пробуем еще раз (или следующую модель)
                    wait_time = 3 + random.uniform(0, 2)
                    logger.warning(f"⚠️ Лимит на {model_name}. Жду {wait_time:.1f}с...")
                    time.sleep(wait_time)
                    continue # Рестарт цикла попыток
                
                elif "404" in error_msg or "NOT_FOUND" in error_msg:
                    logger.warning(f"🚫 Модель {model_name} не найдена (404). Пропускаем.")
                    break # Сразу переходим к СЛЕДУЮЩЕЙ модели в списке
                
                else:
                    logger.warning(f"⚠️ Ошибка {model_name}: {error_msg}")
                    break # Пробуем следующую модель

    logger.error("❌ Ни одна модель не справилась.", exc_info=last_error)
    return _get_fallback_data("Все серверы заняты или недоступны")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП (Офлайн режим)",
        "executive_summary": f"Система AI временно недоступна ({reason}). Менеджер составит КП вручную.",
        "client_pain_points": ["Сбой соединения", "Перегрузка сети"],
        "solution_steps": [],
        "budget_items": [{"item": "Ручной расчет", "price": "По запросу", "time": "1 час"}],
        "why_us": "Мы работаем даже без электричества.",
        "cta": "Позвоните нам"
    }