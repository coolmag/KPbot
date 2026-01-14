import os

# Попробуем G4F (бесплатный), иначе OpenRouter
try:
    import g4f
    USE_G4F = True
except ImportError:
    USE_G4F = False

if USE_G4F:
    # === G4F (GPT4Free) — БЕСПЛАТНО ===
    from g4f.client import Client
    from g4f import Provider

    _g4f_client = None

    # Список провайдеров по приоритету (от лучшего к резервным)
    PROVIDERS = [
        Provider.LambdaChat,
        Provider.You,
        Provider.bing,
        Provider.GPTalk,
        Provider.DeepInfra,
    ]

    def _get_g4f_client():
        global _g4f_client
        if _g4f_client is None:
            _g4f_client = Client()
        return _g4f_client

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

    def get_proposal_text(prompt_data):
        """Генерирует КП через G4F с автоматическим failover провайдеров."""
        client = _get_g4f_client()
        last_error = None

        for provider in PROVIDERS:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_data}
                    ],
                    provider=provider,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_error = e
                print(f"G4F provider {provider.__name__} failed: {e}")
                continue

        # Все провайдеры не работают — пробуем разные модели
        for model in ["claude-3-5-sonnet", "gemini-pro"]:
            for provider in [Provider.You, Provider.LambdaChat]:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt_data}
                        ],
                        provider=provider,
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    print(f"G4F {model} via {provider.__name__} failed: {e}")
                    continue

        return (f"⚠️ Все AI-сервисы временно недоступны.\n\n"
                f"Попробуйте позже или обратитесь к админу.\n\n"
                f"Техническая информация: {last_error}")

else:
    # === OpenRouter (резерв) ===
    import openai

    _client = None

    def _initialize_client():
        global _client
        if _client:
            return _client

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("!!! ВНИМАНИЕ: OPENROUTER_API_KEY не найден.")
            return None

        _client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            max_retries=5,
            default_headers={
                "HTTP-Referer": "https://github.com",
                "X-Title": "ProposalBot",
            },
        )
        return _client

    SYSTEM_PROMPT = """
    Ты — профессиональный копирайтер и маркетолог, который пишет коммерческие предложения для B2B.
    СТРУКТУРА КП: Приветствие → Понимание задачи → Решение → Портфолио → Сроки/Стоимость → Гарантии → Призыв к действию.
    """

    def get_proposal_text(prompt_data):
        """Генерирует КП через OpenRouter."""
        client = _initialize_client()
        if not client:
            return "Ошибка: AI не настроен."

        try:
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct:free",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_data}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Ошибка AI: {e}"


if __name__ == '__main__':
    print(f"Используется: {'G4F' if USE_G4F else 'OpenRouter'}")
    
    test_prompt = """Кто исполнитель: Веб-студия WebArt
Кто клиент: Сеть кофеен CoffeeBreak
Задача: Лендинг с онлайн-заказом"""
    
    print("\nТестовый промпт:")
    print(test_prompt)
    print("\n" + "="*50 + "\n")
    
    result = get_proposal_text(test_prompt)
    print("Результат:")
    print(result)
