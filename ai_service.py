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
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    final_prompt = (
        f"Задача клиента: {prompt}\n"
        f"Данные из интернета (цены и детали): {search_data}\n\n"
        "ИНСТРУКЦИЯ:\n"
        "1. Составь Коммерческое Предложение на РУССКОМ ЯЗЫКЕ.\n"
        "2. Используй найденные цены. Если их нет, придумай реалистичные рыночные цены в рублях.\n"
        "3. Верни ТОЛЬКО валидный JSON (без лишнего текста) по этой схеме:\n"
        "{\n"
        '  "title": "Заголовок КП (на русском)",\n'
        '  "executive_summary": "Суть предложения (на русском)",\n'
        '  "client_pain_points": ["Проблема 1", "Проблема 2"],\n'
        '  "solution_steps": [{"step_name": "Этап 1", "description": "Описание"}],\n'
        '  "budget_items": [{"item": "Услуга", "price": "100 000 руб.", "time": "5 дней"}],\n'
        '  "why_us": "Почему мы (на русском)",\n'
        '  "cta": "Призыв к действию (на русском)"\n'
        "}"
    )

    current_model = get_free_model_id()

    for attempt in range(3):
        try:
            logger.info(f"🧠 Генерация через {current_model} (Попытка {attempt+1})...")
            
            response = client.chat.completions.create(
                model=current_model,
                messages=[
                    # Жестко задаем роль: русский ассистент
                    {"role": "system", "content": "Ты профессиональный бизнес-ассистент. Ты пишешь только на русском языке. Ты возвращаешь только JSON."},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.6,
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            # ... (дальше код тот же: обработка ответа, очистка JSON)
            content = ""
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            elif isinstance(response, dict) and 'choices' in response: # На случай если вернулся dict
                content = response['choices'][0]['message']['content']
            else:
                logger.warning(f"⚠️ Странный ответ от API: {response}")
                raise ValueError("Некорректный формат ответа API")
            # --------------------------------------------------
            
            data = clean_json_response(content)
            
            if data and "title" in data:
                logger.info("✅ Успех! JSON получен.")
                return data
            else:
                logger.warning(f"⚠️ Ответ не содержит валидный JSON. Текст: {content[:100]}...")
                
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
