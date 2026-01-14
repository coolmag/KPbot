import os
import httpx
import logging

# Настраиваем логгер
logger = logging.getLogger(__name__)


def get_proposal_text(prompt):
    """
    Отправляет запрос в Aristotle AI (Harmonic) для генерации коммерческого предложения.
    Бесплатный API с высокой точностью ответов.
    """
    api_key = os.getenv("ARISTOTLE_API_KEY")
    if not api_key:
        logger.error("ARISTOTLE_API_KEY не найден в переменных окружения.")
        return "Ошибка конфигурации: нет ключа API."

    url = "https://aristotle.harmonic.fun/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Системный промпт для коммерческих предложений
    system_prompt = (
        "Ты — профессиональный помощник для составления коммерческих предложений на русском языке. "
        "Твоя задача — на основе краткого описания составить структурированное КП. "
        "Структура: Приветствие, Понимание задачи, Решение, Примерные сроки, Призыв к действию. "
        "Будь краток, убедителен и конкретен."
    )

    data = {
        "model": "aristotle",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    timeout_settings = httpx.Timeout(60.0, connect=15.0)

    try:
        with httpx.Client(timeout=timeout_settings) as client:
            response = client.post(url, headers=headers, json=data)

            if response.status_code == 200:
                response_json = response.json()
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    content = response_json['choices'][0]['message']['content'].strip()
                    logger.info("✅ Aristotle AI: успех")
                    return content
                else:
                    logger.warning(f"Aristotle: пустой ответ: {response.text[:200]}")
            else:
                logger.warning(f"Aristotle ошибка {response.status_code}: {response.text[:200]}")

    except httpx.RequestError as e:
        logger.warning(f"Aristotle сетевая ошибка: {e}")

    return "⚠️ AI-сервис временно недоступен. Попробуйте через минуту."


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

