from openai import OpenAI
from duckduckgo_search import DDGS
import os
import logging
import json
import time
import requests
import random

logger = logging.getLogger(__name__)

def get_free_model_id(exclude_model=None) -> str:
    """
    Возвращает случайную БЕСПЛАТНУЮ модель, исключая проблемные.
    """
    try:
        url = "https://openrouter.ai/api/v1/models"
        response = requests.get(url)
        
        if response.status_code == 200:
            models_data = response.json().get('data', [])
            
            # Фильтр:
            # 1. Должна быть :free
            # 2. Не должна быть 'venice' (они часто требуют $)
            # 3. Не та, которая только что упала (exclude_model)
            free_models = [
                m['id'] for m in models_data 
                if ':free' in m['id'] 
                and 'venice' not in m['id']
                and m['id'] != exclude_model
            ]
            
            if free_models:
                # Берем случайную, чтобы не зависнуть на одной сломанной
                best_model = random.choice(free_models)
                logger.info(f"🎯 Из {len(free_models)} моделей выбрана: {best_model}")
                return best_model
                
        logger.warning("⚠️ Не удалось получить список моделей.")
    except Exception as e:
        logger.error(f"⚠️ Ошибка API списка моделей: {e}")
        
    return "meta-llama/llama-3-8b-instruct:free"

def search_prices(query: str) -> str:
    """Гуглит цены"""
    try:
        clean_query = query.replace("Данные об исполнителе:", "").replace("Данные о клиенте:", "").strip()
        short_query = " ".join(clean_query.split()[-10:])
        logger.info(f"🔎 Гуглю: {short_query}...")
        
        results = DDGS().text(short_query, max_results=3)
        if not results: return ""
            
        context = "Данные из интернета:\n"
        for res in results:
            context += f"- {res['title']}: {res['body']}\n"
        return context
    except Exception:
        return ""

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ Нет ключа API")
        return _get_fallback_data("Нет ключа")

    search_data = search_prices(prompt)
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    final_prompt = (
        f"ЗАДАЧА: {prompt}\n\n"
        f"{search_data}\n\n"
        "ВЕРНИ JSON: {title, executive_summary, client_pain_points[], solution_steps[], budget_items[], why_us, cta}. "
        "Без Markdown."
    )

    current_model = get_free_model_id()

    # Делаем до 3 попыток с РАЗНЫМИ моделями
    for attempt in range(3):
        try:
            logger.info(f"🧠 Генерация через {current_model} (Попытка {attempt+1})...")
            
            response = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": "You output JSON only."},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.7,
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            content = response.choices[0].message.content
            if not content: raise ValueError("Пустой ответ")

            clean_json = content.replace("```json", "").replace("```", "").strip()
            start = clean_json.find('{')
            end = clean_json.rfind('}')
            
            if start != -1 and end != -1:
                data = json.loads(clean_json[start:end+1])
                if "title" in data:
                    logger.info("✅ Успех!")
                    return data
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка {current_model}: {e}")
            # Меняем модель на другую (исключая текущую)
            time.sleep(1)
            current_model = get_free_model_id(exclude_model=current_model)
            continue

    return _get_fallback_data("ИИ занят")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП",
        "executive_summary": f"Ошибка: {reason}",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "-", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }