import os
import re
import logging
import json
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

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

def search_market_price(model_name: str) -> str:
    """Поиск актуальной цены в интернете через DuckDuckGo (Агентная логика)"""
    try:
        results = DDGS().text(f"купить котел {model_name} цена", max_results=3)
        prices_context = "Найденные рыночные цены:\n"
        for r in results:
            prices_context += f"- {r.get('title')}: {r.get('body')}\n"
        return prices_context
    except Exception as e:
        logger.warning(f"Ошибка поиска цены для {model_name}: {e}")
        return "Не удалось получить актуальные цены, используйте цены из базы."

def get_smart_proposal(prompt: str, media_path: str = None, media_type: str = "text") -> dict | None:
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    # 1. Пытаемся вытащить площадь из запроса (текстового)
    area = 100 # по умолчанию
    if prompt:
        area_match = re.search(r'(\d+)\s*(кв|м2|метр)', prompt)
        if area_match:
            area = int(area_match.group(1))

    # 2. ПОДБОР ИЗ КАТАЛОГА (RAG)
    selected_boiler = find_best_boiler(area)
    logger.info(f"✅ Выбран котел из базы: {selected_boiler['model']} за {selected_boiler['price']} руб.")

    # 2.5. АГЕНТСКИЙ ПОИСК ЦЕНЫ В РЕАЛЬНОМ ВРЕМЕНИ
    real_time_prices = search_market_price(selected_boiler['model'])
    logger.info(f"🔍 Рыночные данные по котлу получены.")

    # 3. Формируем умный промпт с передачей структуры JSON
    system_instruction = (
        "Ты — Главный инженер-теплотехник KOTEL.MSK.RU. Твоя задача — спроектировать котельную и составить смету.\n"
        "ОБЯЗАТЕЛЬНЫЕ ИНЖЕНЕРНЫЕ ПРАВИЛА:\n"
        "1. Если площадь дома > 150 м2 или есть запрос на Теплый пол (ТП) и Радиаторы: ОБЯЗАТЕЛЬНО используй Гидроразделитель (гидрострелку) и Коллекторную группу.\n"
        "2. Для горячей воды (ГВС) в больших домах ОБЯЗАТЕЛЬНО добавляй Бойлер косвенного нагрева (БКН) на 150-200л и насос загрузки бойлера.\n"
        "3. На каждый контур (ТП, Радиаторы, БКН) закладывай отдельный циркуляционный насос (например, Grundfos или Wilo).\n"
        "4. Не забывай про группы безопасности, расширительные баки (для отопления и ГВС) и запорную арматуру.\n"
        f"5. ОСНОВНОЙ КОТЕЛ: {selected_boiler['model']} ({selected_boiler['power']} кВт, базовая цена {selected_boiler['price']} руб).\n"
        f"   > АКТУАЛЬНЫЕ РЫНОЧНЫЕ ЦЕНЫ ИЗ ИНТЕРНЕТА: {real_time_prices}\n"
        "   > Скорректируй итоговую цену котла в смете на основе рыночных данных (сделай наценку 10-15%).\n"
        "- Разработай подробную блок-схему на Mermaid.js (graph TD). Разделяй команды строго точкой с запятой (;). "
        "Пример: graph TD; Котел-->Гидрострелка; Гидрострелка-->Коллектор; Коллектор-->НасосТП; Коллектор-->НасосРадиаторов; Котел-->БКН;\n\n"
        "Если пользователь прислал ФОТО помещения: оцени габариты, возможные проблемы (например, мало места) и упомяни это в executive_summary.\n"
        "Если пользователь прислал ГОЛОСОВОЕ сообщение: транскрибируй его смысл и используй для составления сметы.\n"
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

    contents = [system_instruction + f"\n\nЗАПРОС ОТ МЕНЕДЖЕРА: {prompt}"]
    model_name = 'gemma-3-27b-it'

    # Работа с медиа
    uploaded_file = None
    if media_path and media_type in ["photo", "voice"] and os.path.exists(media_path):
        try:
            logger.info(f"📤 Загрузка медиафайла: {media_path}")
            uploaded_file = client.files.upload(file=media_path)
            contents.insert(0, uploaded_file)
            # Для мультимодальных задач используем gemini-2.5-flash
            model_name = 'gemini-2.5-flash'
            logger.info(f"🔄 Переключение на модель {model_name} для обработки {media_type}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки медиа: {e}")

    # Пробуем сгенерировать до 3 раз (Self-Healing Loop)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
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
                
                # Очистка загруженного файла из Google API (опционально, но полезно)
                if uploaded_file:
                    try:
                        client.files.delete(name=uploaded_file.name)
                    except:
                        pass
                        
                return data
                
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ AI выдал невалидный JSON (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logger.error("❌ Фатальный сбой: AI так и не смог выдать правильный JSON.")
                if uploaded_file:
                    try: client.files.delete(name=uploaded_file.name)
                    except: pass
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка API Google: {e}")
            if uploaded_file:
                try: client.files.delete(name=uploaded_file.name)
                except: pass
            return None
            
    return None
