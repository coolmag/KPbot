import os

# === OpenRouter (бесплатные модели) ===
import openai

_client = None

# Бесплатные модели на OpenRouter (обновлено 2026)
FREE_MODELS = [
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "deepseek/deepseek-chat:free",
]

SYSTEM_PROMPT = """
Ты — профессиональный копирайтер и маркетолог, который пишет коммерческие предложения для B2B.

СТРУКТУРА КП:
1. Приветствие (персонализированное под клиента)
2. Понимание задачи (перефразируй потребности клиента)
3. Предлагаемое решение (конкретные этапы работы)
4. Портфолио/опыт
5. Сроки и стоимости (реалистичные оценки или "[Уточняется]")
6. Гарантии и условия
7. Призыв к действию

СТИЛЬ: Профессиональный, конкретный, с фокусом на выгодах для клиента.
Используй нумерованные списки для этапов работы.
"""


def _initialize_client():
    global _client
    if _client:
        return _client

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("!!! ВНИМАНИЕ: OPENROUTER_API_KEY не найден в переменных окружения.")
        return None

    _client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_retries=3,
        default_headers={
            "HTTP-Referer": "https://github.com",
            "X-Title": "AI Client Pilot",
        },
    )
    return _client


def get_proposal_text(prompt_data):
    """Генерирует КП через OpenRouter с авто-выбором модели."""
    client = _initialize_client()
    if not client:
        return "⚠️ AI не настроен. Добавьте OPENROUTER_API_KEY в переменные окружения."

    last_error = None

    for model in FREE_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_data}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            print(f"OpenRouter model {model} failed: {e}")
            continue

    return (f"⚠️ Все AI-сервисы временно недоступны.\n\n"
            f"Попробуйте позже.\n\nТехническая информация: {last_error}")


if __name__ == '__main__':
    print("Тестируем AI...")
    
    if os.getenv("OPENROUTER_API_KEY"):
        test_prompt = """Кто исполнитель: Веб-студия WebArt
Кто клиент: Сеть кофеен CoffeeBreak
Задача: Лендинг с онлайн-заказом"""
    
        result = get_proposal_text(test_prompt)
        print("\n" + "="*50)
        print("Результат:")
        print(result)
    else:
        print("OPENROUTER_API_KEY не найден в .env")
