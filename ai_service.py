from openai import OpenAI
from duckduckgo_search import DDGS
import os
import logging
import json
import time
import re

logger = logging.getLogger(__name__)

# Список самых НАДЕЖНЫХ бесплатных моделей на OpenRouter (проверено по API)
FREE_MODELS = [
    "google/gemma-2-9b-it:free",           # Google Gemma 2 (Очень стабильная)
    "meta-llama/llama-3.1-8b-instruct:free", # Llama 3.1 8B (Легкая и быстрая)
    "huggingfaceh4/zephyr-7b-beta:free",   # Zephyr (Хорошо следует инструкциям)
    "mistralai/mistral-7b-instruct:free",  # Mistral (Классика)
    "microsoft/phi-3-mini-128k-instruct:free" # Microsoft Phi-3 (Маленькая, но удаленькая)
]

def search_prices(query: str) -> str:
    """Гуглит цены через DuckDuckGo"""
    try:
        # Очищаем запрос от лишнего мусора
        clean_query = query.replace("Данные об исполнителе:", "").replace("Данные о клиенте:", "").strip()
        # Берем только последние слова, чтобы поиск был точнее
        short_query = " ".join(clean_query.split()[-10:]) 
        
        logger.info(f"🔎 Гуглю: {short_query}...")
        results = DDGS().text(short_query, max_results=3)
        
        if not results:
            return ""
            
        context = "Найденные данные из интернета (используй их для цен):\n"
        for res in results:
            context += f"- {res['title']}: {res['body']}\n"
        return context
        
    except Exception as e:
        logger.error(f"⚠️ Ошибка поиска: {e}")
        return ""

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ Нет ключа OpenRouter!")
        return _get_fallback_data("Нет API ключа")

    # 1. Поиск (Search)
    search_data = search_prices(prompt)
    
    # 2. ИИ (Generation)
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    final_prompt = (
        f"ЗАДАЧА: {prompt}\n\n"
        f"{search_data}\n\n"
        "ИНСТРУКЦИЯ: Составь коммерческое предложение в формате JSON. "
        "Структура JSON: "
        '{"title": "...", "executive_summary": "...", "client_pain_points": ["..."], '
        '"solution_steps": [{"step_name": "...", "description": "..."}], '
        '"budget_items": [{"item": "...", "price": "...", "time": "..."}], '
        '"why_us": "...", "cta": "..."}. '
        "Важно: Отвечай ТОЛЬКО валидным JSON. Без текста до и после."
    )

    for model in FREE_MODELS:
        try:
            logger.info(f"🧠 Пробую модель: {model}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Ты помощник, который говорит только JSON."}, 
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.7,
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            content = response.choices[0].message.content
            if not content: continue

            # Экстрактор JSON (если модель добавила текст)
            clean_json = content.replace("```json", "").replace("```", "").strip()
            
            # Ищем границы JSON объекта
            start = clean_json.find('{')
            end = clean_json.rfind('}')
            
            if start != -1 and end != -1:
                json_str = clean_json[start:end+1]
                data = json.loads(json_str)
                
                # Валидация полей
                if "title" in data:
                    logger.info(f"✅ Успех! {model} сработала.")
                    return data
            
        except Exception as e:
            logger.warning(f"⚠️ Сбой {model}: {e}")
            time.sleep(1)
            continue

    logger.error("❌ Все модели недоступны.")
    return _get_fallback_data("Сервисы перегружены")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП",
        "executive_summary": f"Не удалось создать КП автоматически ({reason}).",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "Ошибка генерации", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }