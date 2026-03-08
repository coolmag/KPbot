import os
import re
import logging
import json
from google import genai
from google.genai import types

# Импортируем ваши новые файлы
from models import Proposal 
from boiler_catalog import BOILERS

logger = logging.getLogger(__name__)

def find_best_boiler(area: int) -> dict:
    """Простая логика RAG: подбор реального котла из базы по площади"""
    required_power = (area / 10) * 1.2 # +20% запаса
    
    # Ищем подходящий котел, отсортировав каталог по мощности
    suitable_boilers = sorted([b for b in BOILERS if b['power'] >= required_power], key=lambda x: x['power'])
    
    if suitable_boilers:
        return suitable_boilers[0] # Берем минимально подходящий
    return BOILERS[-1] # Если дом огромный, берем самый мощный из базы

def get_smart_proposal(prompt: str) -> dict | None:
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    # 1. Пытаемся вытащить площадь из запроса
    area = 100 # по умолчанию
    area_match = re.search(r'(\d+)\s*(кв|м2|метр)', prompt)
    if area_match:
        area = int(area_match.group(1))

    # 2. ПОДБОР ИЗ КАТАЛОГА (RAG)
    selected_boiler = find_best_boiler(area)
    logger.info(f"✅ Выбран котел из базы: {selected_boiler['model']} за {selected_boiler['price']} руб.")

    # 3. Формируем умный промпт с передачей структуры JSON
    system_instruction = (
        "Ты — Главный инженер-теплотехник KOTEL.MSK.RU. Твоя задача — спроектировать котельную и составить смету.\n"
        "ОБЯЗАТЕЛЬНЫЕ ИНЖЕНЕРНЫЕ ПРАВИЛА:\n"
        "1. Если площадь дома > 150 м2 или есть запрос на Теплый пол (ТП) и Радиаторы: ОБЯЗАТЕЛЬНО используй Гидроразделитель (гидрострелку) и Коллекторную группу.\n"
        "2. Для горячей воды (ГВС) в больших домах ОБЯЗАТЕЛЬНО добавляй Бойлер косвенного нагрева (БКН) на 150-200л и насос загрузки бойлера.\n"
        "3. На каждый контур (ТП, Радиаторы, БКН) закладывай отдельный циркуляционный насос (например, Grundfos или Wilo).\n"
        "4. Не забывай про группы безопасности, расширительные баки (для отопления и ГВС) и запорную арматуру.\n"
        f"5. ОСНОВНОЙ КОТЕЛ: {selected_boiler['model']} ({selected_boiler['power']} кВт, {selected_boiler['price']} руб).\n"
        "- Разработай подробную блок-схему на Mermaid.js (graph TD). Разделяй команды строго точкой с запятой (;). "
        "Пример: graph TD; Котел-->Гидрострелка; Гидрострелка-->Коллектор; Коллектор-->НасосТП; Коллектор-->НасосРадиаторов; Котел-->БКН;\n\n"
        "Верни СТРОГО JSON. Структура:\n"
        "{\n"
        '  "internal_reasoning": "...",\n'
        '  "title": "...",\n'
        '  "executive_summary": "...",\n'
        '  "mermaid_graph": "graph TD; ...",\n'
        '  "client_pain_points": ["Боль клиента 1", "Боль клиента 2"],\n'
        '  "solution_steps": [{"step_name": "Шаг 1", "description": "Описание шага"}],\n'
        '  "plans": [\n'
        '    {"name": "Базовый", "description": "...", "budget_items": [{"item": "Котел", "price": "...", "time": "..."}], "total_price": "..."}\n'
        "  ]\n"
        "}"
    )
    # Пробуем сгенерировать до 3 раз (Self-Healing Loop)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemma-3-27b-it',
                contents=system_instruction + f"\n\nЗАПРОС ОТ МЕНЕДЖЕРА: {prompt}",
                config=types.GenerateContentConfig(temperature=0.3)
            )

            if response.text:
                raw_json = response.text.strip()
                # Срезаем маркдаун
                if raw_json.startswith("```json"): raw_json = raw_json[7:]
                elif raw_json.startswith("```"): raw_json = raw_json[3:]
                if raw_json.endswith("```"): raw_json = raw_json[:-3]
                
                # Пытаемся распарсить
                data = json.loads(raw_json.strip())
                logger.info(f"✅ Успешная AI-генерация с {attempt + 1} попытки!")
                return data
                
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ AI выдал невалидный JSON (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logger.error("❌ Фатальный сбой: AI так и не смог выдать правильный JSON.")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка API Google: {e}")
            return None
            
    return None
