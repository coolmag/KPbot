from google import genai
from google.genai import types
import os
import logging
import json
import time
import re

logger = logging.getLogger(__name__)

def clean_json_response(content: str) -> dict | None:
    try:
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            return json.loads(content[start:end+1])
    except:
        pass
    return None

def get_proposal_json(prompt: str) -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return _get_fallback_data("Нет ключа Google")

    client = genai.Client(api_key=api_key)
    
    # 1. Расчет мощности
    power_kw = "24"
    price_boiler = "120 000"
    
    try:
        area_match = re.search(r'(\d+)\s*(кв|м2|метр)', prompt)
        if area_match:
            area = int(area_match.group(1))
            calc_power = int(area / 10 * 1.2)
            if calc_power > 40: power_kw = "60"
            elif calc_power > 30: power_kw = "45"
            elif calc_power > 24: power_kw = "35"
            
            logger.info(f"🧮 {area}м2 -> {power_kw} кВт")
            
            if power_kw == "60": price_boiler = "420 000"
            elif power_kw == "45": price_boiler = "350 000"
            elif power_kw == "35": price_boiler = "290 000"
    except: pass

    # 2. Промпт (БЕЗОПАСНАЯ СБОРКА СТРОКИ)
    json_structure = '{"title": "Название", "executive_summary": "Описание", "client_pain_points": ["..."], "solution_steps": [{"step_name": "...", "description": "..."}], "budget_items": [{"item": "Котел ' + power_kw + ' кВт", "price": "' + price_boiler + ' руб.", "time": "5 дн."}, {"item": "Бойлер", "price": "...", "time": "..."}], "why_us": "...", "cta": "..."}'
    
    full_prompt = (
        "Ты — Главный инженер KOTEL.MSK.RU. Составь JSON смету.\n"
        f"ВВОДНЫЕ: Дом требует котла {power_kw} кВт (цена ~{price_boiler} руб).\n"
        "ИНСТРУКЦИЯ:\n"
        "1. Описание на русском.\n"
        "2. Исправь ошибки ('конвективы' -> 'конвекторы').\n"
        "3. Верни ТОЛЬКО JSON по схеме:\n" + json_structure + "\n\n"
        f"ЗАПРОС: {prompt}"
    )

    TARGET_MODELS = ["gemma-3-27b-it", "models/gemma-3-27b-it", "gemini-2.0-flash-exp"]

    for model_name in TARGET_MODELS:
        try:
            logger.info(f"⚡ {model_name} генерирует...")
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            
            if response.text:
                data = clean_json_response(response.text)
                if data and "title" in data:
                    logger.info("✅ Успех!")
                    return data
                
        except Exception as e:
            logger.warning(f"Error {model_name}: {e}")
            if "429" in str(e): time.sleep(2)
            continue

    return _get_fallback_data("Сбой")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Смета (Ручной расчет)",
        "executive_summary": f"Ошибка: {reason}",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "-", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }