from openai import OpenAI
import os
import logging
import json
import time

logger = logging.getLogger(__name__)

# Актуальный список моделей на основе твоих скриншотов (Январь 2026)
FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",    # Топ 1: Быстрая и умная
    "meta-llama/llama-3.1-405b-instruct:free",   # Топ 2: Самая мощная (но может быть медленной)
    "nousresearch/hermes-3-llama-3.1-405b:free", # Топ 3: "Гермес" (очень креативная)
    "google/gemma-2-9b-it:free",                 # Запасная (Google Gemma)
]

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ OPENROUTER_API_KEY не найден!")
        return _get_fallback_data("Нет ключа API")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    system_instruction = (
        "Ты — профессиональный составитель Коммерческих Предложений (B2B). "
        "Верни ТОЛЬКО валидный JSON. Без Markdown, без лишних слов. "
        "Структура: title, executive_summary, client_pain_points (list), "
        "solution_steps (list of objects), budget_items (list of objects), why_us, cta. "
        "Цены в рублях."
    )

    for model in FREE_MODELS:
        try:
            logger.info(f"🔄 Пробую модель: {model}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                # Заголовки обязательны для Free Tier
                extra_headers={
                    "HTTP-Referer": "https://telegram.me/KP_Bot", 
                    "X-Title": "KP Generator",
                }
            )
            
            # --- ЗАЩИТА ОТ ПУСТЫХ ОТВЕТОВ (Fix for NoneType error) ---
            if not response or not response.choices:
                logger.warning(f"⚠️ Модель {model} вернула пустой ответ (No choices).")
                continue
                
            content = response.choices[0].message.content
            if not content:
                logger.warning(f"⚠️ Модель {model} вернула пустой текст.")
                continue
            # ---------------------------------------------------------

            # Чистим ответ от ```json и прочего мусора
            clean_json = content.replace("```json", "").replace("```", "").strip()
            
            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError:
                # Иногда Llama пишет "Here is the JSON:" перед скобкой. Ищем первую { и последнюю }
                start = clean_json.find('{')
                end = clean_json.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(clean_json[start:end])
                else:
                    raise ValueError("JSON не найден в ответе")

            # Проверка целостности
            if "title" not in data or "budget_items" not in data:
                logger.warning(f"⚠️ Неполный JSON от {model}")
                continue

            logger.info(f"✅ Успех! Сработала {model}")
            return data

        except Exception as e:
            logger.warning(f"⚠️ Ошибка {model}: {e}")
            time.sleep(1) # Пауза перед следующей попыткой
            continue

    logger.error("❌ Все модели OpenRouter недоступны или перегружены.")
    return _get_fallback_data("Все линии заняты")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП (Режим оффлайн)",
        "executive_summary": f"К сожалению, нейросеть сейчас недоступна ({reason}).",
        "client_pain_points": ["Перегрузка бесплатных каналов"],
        "solution_steps": [],
        "budget_items": [{"item": "Ручной расчет", "price": "По запросу", "time": "-"}],
        "why_us": "Мы работаем над стабильностью.",
        "cta": "Попробуйте позже"
    }