from openai import OpenAI
from duckduckgo_search import DDGS
import os
import logging
import json
import time
import requests
import random
import re

logger = logging.getLogger(__name__)

def get_free_model_id(exclude_model=None) -> str:
    try:
        url = "https://openrouter.ai/api/v1/models"
        response = requests.get(url)
        if response.status_code == 200:
            models_data = response.json().get('data', [])
            free_models = [
                m['id'] for m in models_data 
                if ':free' in m['id'] 
                and 'venice' not in m['id']
                and m['id'] != exclude_model
            ]
            if free_models:
                # Приоритет DeepSeek и Llama, они умные
                # Сортируем так, чтобы deepseek/llama были в начале списка для random.choice
                preferred = [m for m in free_models if 'deepseek' in m or 'llama' in m]
                if preferred and random.random() < 0.7: # 70% шанс взять приоритетную
                    best = random.choice(preferred)
                else:
                    best = random.choice(free_models)
                    
                logger.info(f"🎯 Выбрана модель: {best}")
                return best
    except Exception:
        pass
    return "meta-llama/llama-3-8b-instruct:free"

def search_prices(query: str) -> str:
    try:
        clean_query = query.replace("Данные об исполнителе:", "").replace("Данные о клиенте:", "").strip()
        short_query = " ".join(clean_query.split()[-10:])
        logger.info(f"🔎 Гуглю: {short_query}...")
        results = DDGS().text(short_query, max_results=3)
        if not results: return ""
        context = "Интернет-данные:\n"
        for res in results:
            context += f"- {res['title']}: {res['body']}\n"
        return context
    except Exception:
        return ""

def clean_json_response(content: str) -> dict | None:
    """
    Умная очистка ответа от DeepSeek (мысли) и Markdown.
    """
    try:
        # 1. Удаляем <think>...</think> (мысли DeepSeek)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # 2. Удаляем ```json и ```
        content = content.replace("```json", "").replace("```", "").strip()
        
        # 3. Ищем JSON объект {{...}}
        start = content.find('{')
        end = content.rfind('}')
        
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            return json.loads(json_str)
            
    except Exception as e:
        logger.warning(f"JSON Parse Error: {e}")
        
    return None

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key: return _get_fallback_data("Нет ключа")

    search_data = search_prices(prompt)
    client = OpenAI(base_url="https://openrouter.ai/v1", api_key=api_key)
    
    # Для DeepSeek лучше работает простой промпт
    final_prompt = (
        f"Задача: {prompt}\nContext: {search_data}\n"
        "Output ONLY valid JSON matching this schema:\n"
        "{\"title\": \"str\", \"executive_summary\": \"str\", \"client_pain_points\": [\"str\"], "
        "\"solution_steps\": [{\"step_name\": \"str\", \"description\": \"str\"}], "
        "\"budget_items\": [{\"item\": \"str\", \"price\": \"str\", \"time\": \"str\"}], "
        "\"why_us\": \"str\", \"cta\": \"str\"}"
    )

    current_model = get_free_model_id()

    for attempt in range(3):
        try:
            logger.info(f"🧠 Генерация через {current_model} (Попытка {attempt+1})...")
            
            response = client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": final_prompt}],
                temperature=0.6, # Чуть строже
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            if not response.choices: raise ValueError("Empty choices")
            content = response.choices[0].message.content
            
            data = clean_json_response(content)
            
            if data and "title" in data:
                logger.info("✅ Успех! JSON получен.")
                return data
            else:
                logger.warning(f"⚠️ Ответ не содержит JSON. Длина ответа: {len(content)}")
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка {current_model}: {e}")
            time.sleep(1)
            current_model = get_free_model_id(exclude_model=current_model)
            continue

    return _get_fallback_data("ИИ не смог сгенерировать формат")

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
