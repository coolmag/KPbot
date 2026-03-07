from pathlib import Path

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

    plans_html = build_plans(proposal["plans"])

    html = TEMPLATE.replace("{{client}}", client)
    html = html.replace("{{task}}", task)
    html = html.replace("{{plans}}", plans_html)

    path = Path(f"proposals/{proposal_id}.html")

    path.write_text(html, encoding='utf-8')

    return path
