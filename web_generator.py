import os
from jinja2 import Environment, FileSystemLoader
from github_pages import upload_page

# URL вашего API-сервера на Railway. Должен быть в .env
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# Настраиваем Jinja2 для загрузки шаблонов из текущей директории
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template("proposal_template.html")


def generate_page(proposal_id: str, client: str, task: str, proposal_data: dict):
    # Добавляем total_price к каждому плану, если его нет
    for plan in proposal_data.get("plans", []):
        if "total_price" not in plan:
            total = 0
            for item in plan.get("budget_items", []):
                try:
                    # Убираем все, кроме цифр (пробелы, валюту) и конвертируем в float
                    price_str = ''.join(filter(str.isdigit or str_is_comma, item.get('price', '0').replace(',', '.')))
                    total += float(price_str)
                except ValueError:
                    continue # Игнорируем некорректные цены
            plan["total_price"] = f"{total:,.0f} руб." # Форматируем обратно

    # Рендерим шаблон, передавая в него все необходимые данные
    final_html = template.render(
        proposal_id=proposal_id,
        client=client,
        task=task,
        backend_url=BACKEND_URL,
        mermaid_graph=proposal_data.get("mermaid_graph", ""), # Add this line
        # Передаем все данные из proposal_data напрямую
        **proposal_data 
    )

    # 4. Сохраняем и загружаем на GitHub (через ваш github_pages.py)
    file_path = f"proposals/{proposal_id}.html"
    upload_page(file_path, final_html)
    
    return True

def str_is_comma(s):
    return s == ','
