from pathlib import Path
import os
from github_pages import upload_page

# URL вашего API-сервера на Railway. Должен быть в .env
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

TEMPLATE = Path("template/proposal_template.html").read_text(encoding='utf-8')


def build_plans(plans):
    html = ""
    for p in plans:
        # Умная подсветка: если тариф называется Оптимальный или Премиум, делаем его "Золотым"
        is_premium = "Оптимальный" in p.get('name', '') or "Премиум" in p.get('name', '')
        
        glow_class = "border-[#C5A059]/50 shadow-[0_0_30px_rgba(197,160,89,0.15)] transform -translate-y-2" if is_premium else "border-white/5 hover:border-white/20 hover:-translate-y-1"
        badge = '<div class="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-[#C5A059] text-black text-xs font-bold px-4 py-1 rounded-full uppercase tracking-wider shadow-lg">Рекомендуем</div>' if is_premium else ''
        btn_class = "bg-gradient-to-r from-[#C5A059] to-[#d6b473] text-black hover:shadow-[0_0_20px_rgba(197,160,89,0.4)]" if is_premium else "bg-white/5 text-white hover:bg-white/10 border border-white/10"

        html += f"""
        <div class="relative glass-panel p-8 rounded-3xl cursor-pointer transition-all duration-500 {glow_class} flex flex-col h-full">
            {badge}
            <h3 class="text-3xl font-bold text-white mb-3 tracking-tight">{p.get('name', 'План')}</h3>
            <p class="text-slate-400 text-sm mb-8 leading-relaxed flex-grow">{p.get('description', '')}</p>
            
            <div class="space-y-4 mb-8">
        """
        for item in p.get("budget_items", []):
            html += f"""
                <div class="flex justify-between items-center border-b border-white/5 pb-3 group">
                    <span class="text-slate-300 text-sm flex items-center gap-3">
                        <div class="w-6 h-6 rounded-full bg-[#C5A059]/10 flex items-center justify-center text-[#C5A059]">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
                        </div>
                        {item.get('item', '')}
                    </span>
                    <span class="text-white font-semibold whitespace-nowrap ml-4">{item.get('price', '')}</span>
                </div>
            """
        html += f"""
            </div>
            <button onclick="selectPlan('{p.get('name', 'План')}')" class="w-full py-4 rounded-xl font-bold transition-all duration-300 {btn_class}">
                Выбрать этот тариф
            </button>
        </div>
        """
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
