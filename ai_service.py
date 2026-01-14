import os
import google.generativeai as genai
import logging

# Настраиваем логгер
logger = logging.getLogger(__name__)


def get_proposal_text(prompt):
    """
    Генерирует коммерческое предложение с помощью Google Gemini 1.5 Flash.
    Бесплатный API: 15 запросов в минуту.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY не найден в переменных окружения.")
        return "Ошибка конфигурации: нет ключа API."

    try:
        genai.configure(api_key=api_key)
        
        # Модель Gemini 1.5 Flash - быстрая и бесплатная
        model = genai.GenerativeModel('gemini-1.5-flash')

        system_instruction = (
            "Ты — опытный маркетолог и копирайтер. "
            "Твоя задача — написать текст коммерческого предложения для фрилансера. "
            "Структура КП:\n"
            "1. Приветствие и заголовок\n"
            "2. Понимание задачи клиента\n"
            "3. Предлагаемое решение\n"
            "4. Этапы работы и сроки\n"
            "5. Стоимость (примерная)\n"
            "6. Призыв к действию\n\n"
            "Пиши на русском языке. Будь краток, убедителен и профессионален. "
            "Используй форматирование для удобства чтения."
        )

        full_prompt = f"{system_instruction}\n\n{prompt}"

        response = model.generate_content(full_prompt)
        
        logger.info("✅ Google Gemini: успех")
        return response.text

    except Exception as e:
        logger.error(f"Google Gemini ошибка: {e}")
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

