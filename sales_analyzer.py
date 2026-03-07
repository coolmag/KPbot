import os
import json
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def clean_json(content):

    try:

        content = content.replace("```json", "").replace("```", "")

        start = content.find("{")
        end = content.rfind("}")

        if start != -1 and end != -1:

            return json.loads(content[start:end + 1])

    except Exception as e:

        logger.error(e)

    return None


def analyze_sales(prompt):

    api_key = os.getenv("GOOGLE_API_KEY")

    client = genai.Client(api_key=api_key)

    analysis_prompt = f"""
Ты AI аналитик продаж инженерных систем.

Проанализируй запрос клиента.

Определи:

1 вероятность сделки
2 уровень бюджета
3 главную проблему клиента
4 совет менеджеру

Верни JSON.

Схема:

{{
 "probability": "...%",
 "budget_level": "...",
 "client_problem": "...",
 "manager_tip": "..."
}}

Запрос:

{prompt}
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2
            )
        )

        data = clean_json(response.text)

        return data

    except Exception as e:

        logger.error(e)

        return None
