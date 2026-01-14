import os
import google.generativeai as genai
import httpx
import logging

# Настраиваем логгер
logger = logging.getLogger(__name__)


def get_gemini_proposal(prompt):
    """Генерирует КП через Google Gemini 1.5 Flash."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        system_instruction = (
            "Ты — опытный маркетолог и копирайтер. "
            "Напиши коммерческое предложение для фрилансера. "
            "Структура: Приветствие, Понимание задачи, Решение, Этапы и сроки, Стоимость, Призыв к действию. "
            "Пиши на русском. Будь краток и убедителен."
        )

        response = model.generate_content(f"{system_instruction}\n\n{prompt}")
        logger.info("✅ Google Gemini: успех")
        return response.text

    except Exception as e:
        logger.warning(f"Google Gemini ошибка: {e}")
        return None


def get_aristotle_proposal(prompt):
    """Генерирует КП через Aristotle AI (Harmonic)."""
    api_key = os.getenv("ARISTOTLE_API_KEY")
    if not api_key:
        return None

    url = "https://aristotle.harmonic.fun/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    system_prompt = (
        "Ты — профессиональный помощник для составления коммерческих предложений на русском языке. "
        "Структура: Приветствие, Понимание задачи, Решение, Примерные сроки, Призыв к действию. "
        "Будь краток и убедителен."
    )

    data = {
        "model": "aristotle",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            response = client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                logger.info("✅ Aristotle AI: успех")
                return content
    except Exception as e:
        logger.warning(f"Aristotle ошибка: {e}")

    return None


def get_proposal_text(prompt):
    """Сначала пробуем Gemini, затем Aristotle как fallback."""
    # Пробуем Google Gemini
    result = get_gemini_proposal(prompt)
    if result:
        return result

    # Пробуем Aristotle AI
    result = get_aristotle_proposal(prompt)
    if result:
        return result

    return "⚠️ Все AI-сервисы временно недоступны. Попробуйте через минуту."


if __name__ == '__main__':
    print("Тестируем Aristotle AI...")

    api_key = os.getenv("ARISTOTLE_API_KEY")
    if api_key:
        test_prompt = """Кто исполнитель: Веб-студия WebArt
Кто клиент: Сеть кофеен CoffeeBreak
Задача: Лендинг с онлайн-заказом"""
    
        result = get_proposal_text(test_prompt)
        print("\n" + "="*50)
        print("Результат:")
        print(result)
    else:
        print("ARISTOTLE_API_KEY не найден в переменных окружения")

