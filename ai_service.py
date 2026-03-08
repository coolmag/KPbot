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
        "Ты — Главный инженер и проектировщик котельных KOTEL.MSK.RU.\n"
        "Твоя задача составить детальное коммерческое предложение.\n"
        "ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:\n"
        f"- Используй СТРОГО следующее оборудование: {selected_boiler['model']} ({selected_boiler['power']} кВт).\n"
        f"- Цена котла: {selected_boiler['price']} руб. Добавь к этому стоимость монтажа и труб.\n"
        "- Разбей предложение на 2-3 тарифа (Плана), например: 'Базовый', 'Оптимальный', 'Премиум'.\n"
        "- Разработай логическую блок-схему системы на языке Mermaid.js (graph TD). "
        "Определи, нужен ли бойлер, гидрострелка, коллектор, насосы теплых полов или радиаторов исходя из ТЗ. "
        "ВАЖНО: разделяй команды в Mermaid строго точкой с запятой (;), без переносов строк!\n\n"
        "ВНИМАНИЕ! Твой ответ должен быть СТРОГО валидным JSON без маркдауна и лишнего текста. Соблюдай эту структуру:\n"
        "{\n"
        '  "internal_reasoning": "твой ход мыслей",\n'
        '  "title": "...",\n'
        '  "executive_summary": "...",\n'
        '  "mermaid_graph": "graph TD; A[Котел] --> B[Гидрострелка]; B --> C[Коллектор]; C --> D[Насос Теплого Пола];",'
        '  "client_pain_points": ["Боль клиента 1", "Боль клиента 2"],\n'
        '  "solution_steps": [{"step_name": "Шаг 1", "description": "Описание шага"}],\n'
        '  "plans": [\n'
        '    {"name": "Базовый", "description": "...", "budget_items": [{"item": "Котел", "price": "...", "time": "..."}], "total_price": "..."}\n'
        "  ]\n"
        "}"
    )
    try:
        response = client.models.generate_content(
            model='gemma-3-27b-it',
            contents=system_instruction + f"\n\nЗАПРОС ОТ МЕНЕДЖЕРА: {prompt}",
            config=types.GenerateContentConfig(
                temperature=0.4
                # ❌ МЫ УБРАЛИ response_schema и response_mime_type, чтобы API не ругался
            ),
        )

        if response.text:
            # ✅ Очищаем текст нейросети от возможных markdown-оберток (```json ... ```)
            raw_json = response.text.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:]
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:]
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3]
                
            logger.info("✅ Успешная генерация текста, парсим JSON...")
            return json.loads(raw_json.strip())
            
    except Exception as e:
        logger.error(f"Сбой генерации: {e}")
        return None
