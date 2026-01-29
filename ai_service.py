from openai import OpenAI
from duckduckgo_search import DDGS
import os
import logging
import json
import time

logger = logging.getLogger(__name__)

# Список моделей (Solar Pro 3 и Llama отлично умеют работать с контекстом)
FREE_MODELS = [
    "upstage/solar-pro-3-preview:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "liquid/lfm-2.5-1.2b:free",
]

def search_prices(query: str) -> str:
    """
    Ищет актуальные цены и информацию в DuckDuckGo.
    """
    try:
        logger.info(f"🔎 Ищу в DuckDuckGo: {query}...")
        results = DDGS().text(query, max_results=4)
        if not results:
            return "Нет данных из интернета."
            
        search_context = "Найденная информация из интернета:\n"
        for res in results:
            search_context += f"- {res['title']}: {res['body']}\n"
            
        return search_context
    except Exception as e:
        logger.error(f"⚠️ Ошибка поиска: {e}")
        return "Ошибка поиска данных."

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ OPENROUTER_API_KEY не найден!")
        return _get_fallback_data("Нет ключа API")

    # 1. Сначала ищем информацию в интернете!
    # Вытаскиваем суть запроса из промпта (это грубо, но сработает)
    # Промпт обычно содержит "Задача: Строим котельную..."
    # Мы просто поищем по всему тексту задачи.
    search_query = f"цена стоимость {prompt[-100:]}" # Берем последние 100 символов (сама задача)
    search_data = search_prices(search_query)
    
    logger.info("🧠 Данные найдены, отправляю в ИИ...")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    # 2. Формируем умный промпт с контекстом
    final_prompt = (
        f"ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:\n{prompt}\n\n"
        f"{search_data}\n\n" # <--- Вставляем найденные цены!
        "ИНСТРУКЦИЯ:\n"
        "Используя найденную информацию (если она полезна), составь КП в формате JSON. "
        "Если точных цен нет, дай экспертную оценку на основе данных. "
        "Структура JSON: {title, executive_summary, client_pain_points, solution_steps, budget_items, why_us, cta}."
    )

    system_instruction = "Ты — эксперт по продажам. Отвечай ТОЛЬКО валидным JSON."

    for model in FREE_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.7,
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            content = response.choices[0].message.content
            if not content: continue

            # Очистка JSON
            clean_json = content.replace("```json", "").replace("```", "").strip()
            start = clean_json.find('{')
            end = clean_json.rfind('}')
            if start != -1 and end != -1:
                clean_json = clean_json[start:end+1]
            
            data = json.loads(clean_json)
            if "title" in data:
                logger.info(f"✅ Успех! {model} справилась.")
                return data

        except Exception as e:
            logger.warning(f"⚠️ Ошибка {model}: {e}")
            continue

    return _get_fallback_data("ИИ недоступен")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП",
        "executive_summary": "Не удалось сгенерировать КП.",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [],
        "why_us": "-",
        "cta": "-"
    }
