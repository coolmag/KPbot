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

# ... (функции clean_json_response, get_free_model_id, search_prices оставляем БЕЗ изменений) ...
# (Если они у тебя сохранились - отлично. Если нет - скопируй из моего предыдущего сообщения)
# Для надежности дублирую ВЕСЬ файл целиком ниже:

def get_free_model_id(exclude_model=None) -> str:
    try:
        url = "https://openrouter.ai/api/v1/models"
        response = requests.get(url)
        if response.status_code == 200:
            models_data = response.json().get('data', [])
            good = ['deepseek', 'llama-3.3', 'gemini-2', '70b', 'mistral-large']
            bad = ['1b', '3b', 'venice', 'liquid', 'chimera', 'vision'] 
            candidates = []
            for m in models_data:
                mid = m['id'].lower()
                if ':free' not in mid: continue
                if any(b in mid for b in bad): continue
                if mid == exclude_model: continue
                if any(g in mid for g in good) or '8b' in mid:
                    candidates.append(m['id'])
            
            if candidates:
                top = [c for c in candidates if 'deepseek' in c or '70b' in c]
                return random.choice(top) if top else random.choice(candidates)
    except: pass
    return "google/gemini-2.0-flash-exp:free"

def search_prices(query: str) -> str:
    """Ищет цены под конкретную мощность"""
    try:
        area_match = re.search(r'(\d+)\s*(кв|м2|метр)', query)
        power_kw = "24"
        if area_match:
            area = int(area_match.group(1))
            power_kw = str(int(area / 10 * 1.2))
            logger.info(f"🧮 Дом {area}м2 -> Котел {power_kw} кВт")
        
        search_q = f"цена газовый котел {power_kw} кВт Viessmann Buderus 2025"
        logger.info(f"🔎 Гуглю: {search_q}")
        
        results = DDGS().text(search_q, max_results=4)
        context = f"РЫНОЧНЫЕ ЦЕНЫ (Котел {power_kw} кВт):\n"
        if results:
            for res in results:
                context += f"- {res['title']}: {res['body']}\n"
        return context
    except Exception: return "Цены: 150 000 руб."

def clean_json_response(content: str) -> dict | None:
    try:
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            return json.loads(content[start:end+1])
    except: pass
    return None

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key: return _get_fallback_data("Нет ключа")

    # 1. Сначала считаем мощность и ищем цену
    search_data = search_prices(prompt)
    
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    role_instruction = (
        "Ты — Главный инженер KOTEL.MSK.RU (30 лет опыта).\n"
        "ТВОЯ ЗАДАЧА: Подобрать оборудование СТРОГО под площадь дома.\n"
        "ПРАВИЛО МОЩНОСТИ: 1 кВт на 10 м2. Если дом 450 м2 — котел должен быть 50-60 кВт. "
        "ПРАВИЛО ЦЕН: Бери цены из поиска. Если их нет — ставь рыночные."
    )
    
    final_prompt = f\"\"\"ЗАПРОС: {prompt}
НАЙДЕННЫЕ ЦЕНЫ: {search_data}

ВЕРНИ JSON (без Markdown):
{{
  "title": "Название (укажи мощность котла)",
  "executive_summary": "Описание...",
  "client_pain_points": ["..."],
  "solution_steps": [{{ "step_name": "...", "description": "..." }}],
  "budget_items": [{{ "item": "Наименование (бренд, мощность)", "price": "X руб.", "time": "X дн." }}],
  "why_us": "...",
  "cta": "..."
}}
\"\"\"

    current_model = get_free_model_id()

    for attempt in range(3):
        try:
            logger.info(f"🧠 {current_model} генерирует...")
            response = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": role_instruction},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.4,
                extra_headers={"HTTP-Referer": "https://tg.me", "X-Title": "KP Bot"}
            )
            
            content = ""
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            elif isinstance(response, dict) and 'choices' in response:
                content = response['choices'][0]['message']['content']
            
            data = clean_json_response(content)
            
            if data and "title" in data:
                return data
                
        except Exception as e:
            logger.warning(f"Error {current_model}: {e}")
            time.sleep(1)
            current_model = get_free_model_id(exclude_model=current_model)
            continue

    return _get_fallback_data("Ошибка")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Черновик КП",
        "executive_summary": "Ошибка генерации.",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "Ошибка", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }
