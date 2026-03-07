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

    # 1. Пытаемся вытащить площадь из запроса (как было у вас)
    area = 100 # по умолчанию
    area_match = re.search(r'(\d+)\s*(кв|м2|метр)', prompt)
    if area_match:
        area = int(area_match.group(1))

    # 2. ПОДБОР ИЗ КАТАЛОГА (RAG)
    selected_boiler = find_best_boiler(area)
    logger.info(f"✅ Выбран котел из базы: {selected_boiler['model']} за {selected_boiler['price']} руб.")

    # 3. Формируем умный промпт с передачей реальных данных
    system_instruction = f"""Ты — Главный инженер и менеджер по продажам KOTEL.MSK.RU.
Твоя задача составить детальное коммерческое предложение.
ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:
- Используй СТРОГО следующее оборудование: {selected_boiler['model']} ({selected_boiler['power']} кВт).
- Цена котла: {selected_boiler['price']} руб. Добавь к этому стоимость монтажа и труб.
- Разбей предложение на 2-3 тарифа (Плана), например: 'Базовый', 'Оптимальный', 'Премиум'.
- Сначала напиши свои рассуждения в поле 'internal_reasoning', а затем заполни схему.
"""

    # Добавляем фиктивное поле internal_reasoning, чтобы заставить модель "думать" перед ответом
    # Google GenAI SDK позволяет передать Pydantic модель прямо в response_schema
    # Это гарантирует 100% валидный JSON
    try:
        response = client.models.generate_content(
            model='gemma-3-27b-it',
            contents=system_instruction + f"\n\nЗАПРОС ОТ МЕНЕДЖЕРА: {prompt}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                # Мы просим вернуть JSON, соответствующий вашей модели Proposal (из models.py)
                response_schema=Proposal, 
                temperature=0.4
            ),
        )

        if response.text:
            logger.info("✅ Успешная генерация!")
            return json.loads(response.text)
    except Exception as e:
        logger.error(f"Сбой генерации: {e}")
        return None
