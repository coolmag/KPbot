import openai
import os

# --- ИНТЕГРАЦИЯ С OPENROUTER (С "ЛЕНИВОЙ" ИНИЦИАЛИЗАЦИЕЙ) ---

# Глобальная переменная для кеширования клиента
_client = None

def _initialize_client():
    """
    Инициализирует и возвращает AI-клиент. Выполняется только один раз.
    """
    global _client
    if _client:
        return _client

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("!!! ВНИМАНИЕ: OPENROUTER_API_KEY не найден. AI-сервис не будет работать.")
        return None

    project_name = "ProposalBot"
    project_url = "https://github.com"

    _client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_retries=5,
        default_headers={
            "HTTP-Referer": project_url,
            "X-Title": project_name,
        },
    )
    return _client


# Улучшенный системный промпт
SYSTEM_PROMPT = """
Ты — профессиональный копирайтер и маркетолог, который пишет коммерческие предложения для B2B.

Твоя задача — на основе предоставленных данных создать убедительное КП:

СТРУКТУРА КП:
1. Приветствие (персонализированное под клиента)
2. Понимание задачи (перефразируй потребности клиента своими словами)
3. Предлагаемое решение (конкретные этапы работы)
4. Портфолио/опыт (свяжи с контекстом задачи)
5. Сроки и стоимости (реалистичные оценки или "[Уточняется]")
6. Гарантии и условия
7. Призыв к действию

СТИЛЬ:
- Профессиональный, но дружелюбный
- Конкретный (избегай размытых фраз)
- Фокус на выгодах для клиента
- Используй нумерованные списки для этапов
"""


def get_proposal_text(prompt_data):
    """
    Генерирует текст КП на основе структурированных данных.
    
    Args:
        prompt_data: Строка с информацией о вас, клиенте и задаче
    """
    client = _initialize_client()
    if not client:
        return "Ошибка: AI-клиент не инициализирован. Проверьте OPENROUTER_API_KEY."

    ai_model = "mistralai/mistral-7b-instruct:free"

    try:
        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_data}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"!!! Ошибка AI: {e}")
        return f"Ошибка генерации: {e}"


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    if os.getenv("OPENROUTER_API_KEY"):
        test_prompt = """Кто исполнитель: Веб-студия WebArt, делаем сайты 5 лет
Кто клиент: Сеть кофеен CoffeeBreak, 15 точек в Москве
Задача: Лендинг для новой кофейни с онлайн-заказом и доставкой"""
        
        print("Тестовый промпт:")
        print(test_prompt)
        print("\n" + "="*50 + "\n")
        
        proposal = get_proposal_text(test_prompt)
        print("Результат:")
        print(proposal)
    else:
        print("Ключ OPENROUTER_API_KEY не найден")
