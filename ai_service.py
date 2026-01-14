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
    project_url = "https://github.com" # URL можно указать любой, это для заголовков

    # УВЕЛИЧИВАЕМ КОЛИЧЕСТВО ПОПЫТОК СОЕДИНЕНИЯ ДО 5
    _client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_retries=5, # <-- Вот это изменение
        default_headers={
            "HTTP-Referer": project_url,
            "X-Title": project_name,
        },
    )
    return _client

def get_proposal_text(prompt):
    """
    Отправляет промпт в AI API и возвращает сгенерированный текст
    коммерческого предложения.
    """
    client = _initialize_client()
    if not client:
        return "Ошибка: AI-клиент не был инициализирован. Проверьте наличие OPENROUTER_API_KEY в переменных окружения Railway."

    # ВРЕМЕННОЕ РЕШЕНИЕ: Жестко задаем модель, чтобы обойти ошибку сборки Railway
    ai_model = "mistralai/mistral-7b-instruct:free"

    try:
        # Универсальный промпт для AI
        system_prompt = """
Ты — AI-ассистент, который помогает фрилансерам составлять коммерческие предложения (КП).
Твоя задача — на основе краткого описания проекта от пользователя сгенерировать структурированный, вежливый и убедительный текст для КП.

Структура ответа должна быть такой:
1. Вежливое обращение.
2. Понимание задачи (кратко перефразируй, что нужно сделать).
3. Предлагаемое решение (что конкретно будет сделано, какие этапы).
4. Сроки и стоимость (используй заглушки, например, "[Сроки будут уточнены]" и "[Стоимость будет рассчитана]").
5. Призыв к действию (например, "Готов обсудить детали и ответить на ваши вопросы").

Стиль: Профессиональный, но дружелюбный.
"""

        response = client.chat.completions.create(
            model=ai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"!!! Произошла критическая ошибка при обращении к AI-сервису: {e}")
        return f"Ошибка AI: Не удалось сгенерировать текст. Проверьте консоль, где запущен бот, для деталей."

if __name__ == '__main__':
    # Пример для тестирования модуля локально
    from dotenv import load_dotenv
    load_dotenv()
    
    # Тест запускается только если есть ключ
    if os.getenv("OPENROUTER_API_KEY"):
        # Используем ту же модель, что и в основной функции для консистентности
        print(f"Тестируем с моделью: {'mistralai/mistral-7b-instruct:free'}")
        test_prompt = "Нужно сделать лендинг для кофейни. Стильный, современный, с картой."
        proposal = get_proposal_text(test_prompt)
        print("--- Сгенерированное предложение ---")
        print(proposal)
    else:
        print("Ключ OPENROUTER_API_KEY не найден в .env файле. Невозможно выполнить тест.")
