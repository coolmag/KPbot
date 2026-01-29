from openai import OpenAI
from duckduckgo_search import DDGS
import os
import logging
import json
import time
import requests

logger = logging.getLogger(__name__)

def get_free_model_id() -> str:
    """
    Спрашивает у OpenRouter список всех доступных моделей
    и возвращает первую попавшуюся бесплатную.
    """
    try:
        url = "https://openrouter.ai/api/v1/models"
        response = requests.get(url)
        
        if response.status_code == 200:
            models_data = response.json().get('data', [])
            # Ищем модели, у которых в ID есть ':free'
            free_models = [m['id'] for m in models_data if ':free' in m['id']]
            
            if free_models:
                # Сортируем: ставим Llama и Mistral вперед, если они есть
                # (они обычно самые адекватные для JSON)
                free_models.sort(key=lambda x: 0 if 'llama' in x or 'mistral' in x else 1)
                
                best_model = free_models[0]
                logger.info(f"🎯 Найдены бесплатные модели ({len(free_models)}). Выбрана: {best_model}")
                return best_model
                
        logger.warning("⚠️ Не удалось найти бесплатные модели в списке API.")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при поиске моделей: {e}")
        
    # Если автопоиск сломался, возвращаем жесткий fallback (вдруг заработает)
    return "meta-llama/llama-3.2-3b-instruct:free"

def search_prices(query: str) -> str:
    """Гуглит цены через DuckDuckGo"""
    try:
        clean_query = query.replace("Данные об исполнителе:", "").replace("Данные о клиенте:", "").strip()
        short_query = " ".join(clean_query.split()[-10:]) 
        logger.info(f"🔎 Гуглю: {short_query}...")
        
        results = DDGS().text(short_query, max_results=3)
        if not results: return ""
            
        context = "Найденные данные из интернета (используй их для цен):\n"
        for res in results:
            context += f"- {res['title']}: {res['body']}\n"
        return context
    except Exception:
        return ""

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("❌ Нет ключа OpenRouter!")
        return _get_fallback_data("Нет API ключа")

    # 1. Поиск
    search_data = search_prices(prompt)
    
    # 2. Авто-выбор модели
    model_id = get_free_model_id()
    
    # 3. Генерация
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    final_prompt = (
        f"ЗАДАЧА: {prompt}\n\n"
        f"{search_data}\n\n"
        "ИНСТРУКЦИЯ: Верни JSON объект коммерческого предложения. "
        "Поля: title, executive_summary, client_pain_points (list), "
        "solution_steps (list of objects: step_name, description), "
        "budget_items (list of objects: item, price, time), why_us, cta. "
        "ВАЖНО: ТОЛЬКО JSON. Без Markdown."
    )

    # Делаем 2 попытки (вдруг выбранная модель глюкнет)
    for attempt in range(2):
        try:
            logger.info(f"🧠 Генерация через {model_id} (Попытка {attempt+1})...")
            
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "You are a JSON generator."},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.7,
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            content = response.choices[0].message.content
            if not content: raise ValueError("Пустой ответ")

            # Очистка
            clean_json = content.replace("```json", "").replace("```", "").strip()
            start = clean_json.find('{')
            end = clean_json.rfind('}')
            
            if start != -1 and end != -1:
                data = json.loads(clean_json[start:end+1])
                if "title" in data:
                    logger.info("✅ Успех!")
                    return data
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка {model_id}: {e}")
            # Если не вышло, пробуем найти ДРУГУЮ модель
            time.sleep(1)
            model_id = get_free_model_id() # Перевыбираем
            continue

    return _get_fallback_data("ИИ временно недоступен")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП",
        "executive_summary": f"Ошибка генерации ({reason}).",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "-", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }
