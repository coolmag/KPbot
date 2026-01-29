import google.generativeai as genai
import os
import logging
import json
import time
import random

logger = logging.getLogger(__name__)

# Настраиваем API один раз
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def get_proposal_json(prompt: str) -> dict:
    if not api_key:
        logger.error("❌ GOOGLE_API_KEY не найден.")
        return _get_fallback_data("Нет ключа")

    # Используем 'gemini-pro' - это алиас, который Google обычно держит живым
    # Если он умрет, попробуем 'gemini-1.5-flash-latest'
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "models/gemini-1.5-flash"
    ]

    system_instruction = (
        "Ты — бизнес-ассистент. Твоя задача — вернуть JSON структуру КП. "
        "НЕ используй Markdown. "
        "Формат: {title, executive_summary, client_pain_points[], solution_steps[], budget_items[], why_us, cta}."
    )
    
    # Объединяем системный промпт и пользовательский, так как в старом API
    # system_instruction не всегда поддерживается корректно
    full_prompt = f"{system_instruction}\n\nЗАДАЧА:\n{prompt}\n\nJSON:"

    for model_name in models_to_try:
        try:
            logger.info(f"🔄 Пробую Google (v0.8.3): {model_name}...")
            
            model = genai.GenerativeModel(model_name)
            
            # generation_config для JSON
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    response_mime_type="application/json" # Пытаемся форсировать JSON
                )
            )
            
            if not response.text:
                raise ValueError("Пустой ответ")

            # Чистим
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
            if "title" not in data:
                continue

            logger.info(f"✅ Успех! {model_name} сработала.")
            return data

        except Exception as e:
            if "429" in str(e):
                logger.warning(f"⏳ 429 на {model_name}. Жду 5 сек...")
                time.sleep(5)
            elif "404" in str(e):
                logger.warning(f"🚫 {model_name} не найдена.")
            else:
                logger.warning(f"⚠️ Ошибка {model_name}: {e}")
            continue

    return _get_fallback_data("Google API недоступен")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП (Сбой сети)",
        "executive_summary": f"Не удалось связаться с AI ({reason}).",
        "client_pain_points": ["Ошибка соединения"],
        "solution_steps": [],
        "budget_items": [{"item": "-", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "Повторите позже"
    }
