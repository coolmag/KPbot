import os
import logging
import json
import time
import re

from google import genai
from google.genai import types

from models import Proposal
from boiler_catalog import BOILERS

logger = logging.getLogger(__name__)


def clean_json_response(content: str):
    try:
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find("{")
        end = content.rfind("}")

        if start != -1 and end != -1:
            return json.loads(content[start:end + 1])

    except Exception as e:
        logger.error(f"JSON parse error {e}")

    return None


def select_boiler(area):
    for boiler in BOILERS:
        if area <= boiler["area_max"]:
            return boiler
    return BOILERS[-1]


def extract_area(prompt):
    area_match = re.search(r"(\d+)\s*(кв|м2|метр)", prompt)
    if not area_match:
        return None
    return int(area_match.group(1))


def build_prompt(prompt: str):
    area = extract_area(prompt)

    if area:
        boiler = select_boiler(area)
        power = boiler["power"]
        price = boiler["price"]
        model = boiler["model"]
    else:
        power = 24
        price = 120000
        model = "Стандартный котел"

    json_schema = """
{
"title": "...",
"executive_summary": "...",
"client_pain_points": ["..."],
"solution_steps": [
 {"step_name": "...", "description": "..."}
],
"plans":[
 {
  "name":"Эконом",
  "description":"...",
  "budget_items":[
   {"item":"...", "price":"...", "time":"..."}
  ]
 },
 {
  "name":"Стандарт",
  "description":"...",
  "budget_items":[
   {"item":"...", "price":"...", "time":"..."}
  ]
 },
 {
  "name":"Премиум",
  "description":"...",
  "budget_items":[
   {"item":"...", "price":"...", "time":"..."}
  ]
 }
],
"why_us":"...",
"cta":"..."
}
"""

    full_prompt = f"""
Ты ведущий инженер отопительных систем.

Составь профессиональное коммерческое предложение.

Дом требует котел {power} кВт.
Рекомендуемая модель котла: {model}
Ориентировочная цена: {price} руб.

Сделай 3 варианта решения:

Эконом
Стандарт
Премиум

Включи модель котла {model} в один из планов.

Верни ТОЛЬКО JSON.

Схема:

{json_schema}

Запрос клиента:

{prompt}
"""

    return full_prompt


def get_proposal_json(prompt: str):

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise Exception("Нет GOOGLE_API_KEY")

    client = genai.Client(api_key=api_key)

    full_prompt = build_prompt(prompt)

    models = [
        "gemma-3-27b-it",
        "models/gemma-3-27b-it",
        "gemini-2.0-flash-exp",
    ]

    for model in models:

        try:

            logger.info(f"AI generating via {model}")

            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                ),
            )

            if not response.text:
                continue

            data = clean_json_response(response.text)

            if not data:
                continue

            proposal = Proposal(**data)

            return proposal.model_dump()

        except Exception as e:

            logger.warning(e)

            if "429" in str(e):
                time.sleep(2)

            continue

    raise Exception("AI generation failed")
