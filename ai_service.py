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
        # Чистим от маркдауна и лишнего текста
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
    
    # 1. Логика Инженера: Считаем мощность сами, раз Gemma не умеет гуглить
    power_kw = "24"
    price_boiler = "280 000" # Примерная цена мощного котла
    
    try:
        area_match = re.search(r'(\d+)\s*(кв|м2|метр)', prompt)
        if area_match:
            area = int(area_match.group(1))
            # Формула: 1 кВт на 10 м2 + 20%
            calc_power = int(area / 10 * 1.2) 
            # Округляем до стандартных мощностей
            if calc_power > 40: power_kw = "60"
            elif calc_power > 30: power_kw = "45"
            elif calc_power > 24: power_kw = "35"
            
            logger.info(f"🧮 Дом {area}м2 -> Котел {power_kw} кВт")
            
            # Корректируем цену в зависимости от мощности
            if power_kw == "60": price_boiler = "420 000"
            elif power_kw == "45": price_boiler = "350 000"
            elif power_kw == "35": price_boiler = "290 000"
            else: price_boiler = "120 000" # 24 кВт
    except: pass

    # 2. Промпт (Вшиваем инструкции внутрь, так как Gemma не понимает system_instruction)
    full_prompt = (
        "Ты — Главный инженер KOTEL.MSK.RU. Твоя задача — составить JSON для сметы.\n"
        f"ВВОДНЫЕ ДАННЫЕ: Дом клиента требует котла мощностью {power_kw} кВт.\n"
        f"Ориентировочная цена такого котла (Buderus/Viessmann): {price_boiler} руб.\n\n"
        "ИНСТРУКЦИЯ:\n"
        "1. Составь описание решения на русском языке.\n"
        "2. Исправь ошибки (напр. 'конвективы' -> 'конвекторы').\n"
        "3. Верни ОТВЕТ ТОЛЬКО В ФОРМАТЕ JSON (без вступлений).\n\n"
        "СХЕМА JSON:\n"
        "{\n"
        '  "title": "Название (например: Проект котельной ' + power_kw + ' кВт)",\n'
        '  "executive_summary": "Описание...",\n'
        '  "client_pain_points": ["..."],\n'
        '  "solution_steps": [{"step_name": "...", "description": "..."}],\n'
        '  "budget_items": [\n'
        '     {"item": "Котел газовый ' + power_kw + ' кВт", "price": "' + price_boiler + ' руб.", "time": "5 дн."},
'
        '     {"item": "Бойлер косвенного нагрева", "price": "...", "time": "..."}
'
        '  ],\n'
        '  "why_us": "...",\n'
        '  "cta": "..."
'
        "}\n\n"
        f"ЗАПРОС КЛИЕНТА: {prompt}"
    )

    # Используем Gemma 3 27B (у неё лимит 14k)
    # Если она недоступна, пробуем Gemini 2.0 Flash
    TARGET_MODELS = [
        "gemma-3-27b-it",
        "models/gemma-3-27b-it",
        "gemini-2.0-flash-exp"
    ]

    for model_name in TARGET_MODELS:
        try:
            logger.info(f"⚡ Генерация через {model_name}...")
            
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                    # Убрали system_instruction и json mode, чтобы Gemma не падала
                )
            )
            
            if response.text:
                data = clean_json_response(response.text)
                if data and "title" in data:
                    logger.info(f"✅ Успех ({model_name})!")
                    return data
                
        except Exception as e:
            logger.info(f"⚠️ Ошибка {model_name}: {e}")
            if "429" in str(e): # Лимиты
                time.sleep(2)
            continue

    return _get_fallback_data("Сбой генерации")

def _get_fallback_data(reason: str) -> dict:
    return {
        "title": "Смета (Расчет инженером)",
        "executive_summary": f"Ошибка AI: {reason}. Мы составим смету вручную.",
        "client_pain_points": [],
        "solution_steps": [],
        "budget_items": [{"item": "-", "price": "-", "time": "-"}],
        "why_us": "-",
        "cta": "-"
    }
