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
    
    # --- МОЩНЫЙ ИНЖЕНЕРНЫЙ ПРОМПТ ---
    role_instruction = (
        "Ты — Главный инженер-проектировщик систем отопления с 30-летним стажем. "
        "Твоя специализация — энергоэффективные котельные (Buderus, Viessmann, Vaillant). "
        "Твоя задача — составить профессиональное КП. "
        "\nВАЖНО: ИСПРАВЛЯЙ ТЕХНИЧЕСКИЕ ОШИБКИ КЛИЕНТА. "
        "Например, если клиент пишет 'Котел на 5 контуров', ты понимаешь, что это "
        "'Котел + коллекторная группа на 5 контуров (насосные группы)'. "
        "Пиши технически грамотно, используй термины: гидрострелка, бойлер косвенного нагрева, погодозависимая автоматика."
    )
    
    final_prompt = (
        f"ЗАДАЧА КЛИЕНТА: {prompt}\n"
        f"ТЕХНИЧЕСКИЕ ДАННЫЕ (Цены/Аналоги): {search_data}\n\n"
        "ИНСТРУКЦИЯ:\n"
        "1. Составь КП на РУССКОМ ЯЗЫКЕ.\n"
        "2. В разделе 'Решение' опиши грамотную схему котельной.\n"
        "3. В смете укажи реальное оборудование (Котел, Бойлер, Насосные группы, Обвязка).\n"
        "4. Верни ТОЛЬКО валидный JSON по схеме:\n"
        "{\n"
        '  "title": "Заголовок",\n'
        '  "executive_summary": "Краткое описание решения",\n'
        '  "client_pain_points": ["Риск 1 (напр. перерасход газа)", "Риск 2 (напр. скачки давления)"],\n'
        '  "solution_steps": [{"step_name": "Проектирование", "description": "Теплотехнический расчет..."}],\n'
        '  "budget_items": [{"item": "Конденсационный котел 60 кВт", "price": "...", "time": "..."}],\n'
        '  "why_us": "Опыт 30 лет, гарантия на швы",\n'
        '  "cta": "Выезд инженера"\n'
        "}"
    )

    current_model = get_free_model_id()

    for attempt in range(3):
        try:
            logger.info(f"🧠 Инженер {current_model} думает (Попытка {attempt+1})...")
            
            response = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": role_instruction}, # Вставляем роль
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.5, # Делаем его более строгим и логичным
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            content = ""
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            elif isinstance(response, dict) and 'choices' in response: # На случай если вернулся dict
                content = response['choices'][0]['message']['content']
            else:
                logger.warning(f"⚠️ Странный ответ от API: {response}")
                raise ValueError("Некорректный формат ответа API")
            
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
