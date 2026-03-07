from pathlib import Path
import os

# URL вашего API-сервера на Railway. Должен быть в .env
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

TEMPLATE = Path("template/proposal_template.html").read_text(encoding='utf-8')


def build_plans(plans):
    html = ""
    for plan in plans:
        html += f"""
        <div class="plan">
        <h3>{plan['name']}</h3>
        <p>{plan['description']}</p>
        <ul>
        """
        for item in plan["budget_items"]:
            html += f"<li>{item['item']} — {item['price']}</li>"
        html += "</ul></div>"
    return html


def generate_page(proposal_id, client, task, proposal):
    """Генерирует HTML-страницу из шаблона и данных."""
    
    plans_html = build_plans(proposal.get("plans", []))

    # Заменяем все плейсхолдеры
    html = TEMPLATE.replace("{{client}}", client)
    html = html.replace("{{task}}", task)
    html = html.replace("{{plans}}", plans_html)
    html = html.replace("{{proposal_id}}", str(proposal_id))
    html = html.replace("{{backend_url}}", BACKEND_URL)

    path = Path(f"proposals/{proposal_id}.html")
    # Надежно создаем директорию, если она не существует
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding='utf-8')

    return path
