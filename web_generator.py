from pathlib import Path
import os
from github_pages import upload_page

# URL вашего API-сервера на Railway. Должен быть в .env
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

TEMPLATE = Path("template/proposal_template.html").read_text(encoding='utf-8')


def build_plans(plans):
    html = ""
    for p in plans:
        html += f"""
        <div class="glass p-8 rounded-2xl">
        <h3 class="text-xl font-semibold">
        {p.get('name', 'План')}
        </h3>
        <p class="mt-4 text-slate-300">
        {p.get('description', '')}
        </p>
        <ul class="mt-6 text-slate-400 space-y-2">
        """
        for item in p.get("budget_items", []):
            html += f"<li>✔ {item.get('item', '')} — <b>{item.get('price', '')}</b></li>"
        html += "</ul></div>"
    return html


def generate_page(proposal_id, client, task, proposal):
    """Генерирует HTML-страницу и загружает её на GitHub."""
    
    plans_html = build_plans(proposal.get("plans", []))

    # Заменяем все плейсхолдеры
    html = TEMPLATE.replace("{{client}}", client)
    html = html.replace("{{task}}", task)
    html = html.replace("{{plans}}", plans_html)
    html = html.replace("{{proposal_id}}", str(proposal_id))
    html = html.replace("{{backend_url}}", BACKEND_URL)

    # Загружаем сгенерированный HTML напрямую на GitHub
    upload_page(f"{proposal_id}.html", html)
