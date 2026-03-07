from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3

app = FastAPI()


def get_proposal(proposal_id):

    conn = sqlite3.connect("proposals.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT client, task, created_at FROM proposals WHERE id=?",
        (proposal_id,)
    )

    row = cursor.fetchone()

    conn.close()

    return row


@app.get("/proposal/{proposal_id}", response_class=HTMLResponse)
def show_proposal(proposal_id: int):

    data = get_proposal(proposal_id)

    if not data:
        return "<h1>Предложение не найдено</h1>"

    client, task, date = data

    html = f"""
    <html>
    <head>
        <title>Коммерческое предложение</title>
        <style>

        body {{
            font-family: Arial;
            max-width: 900px;
            margin: auto;
            padding: 40px;
        }}

        .box {{
            background: #f4f4f4;
            padding: 20px;
            border-radius: 10px;
        }}

        .btn {{
            background: #1a252f;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            text-decoration: none;
        }}

        </style>
    </head>

    <body>

    <h1>Коммерческое предложение</h1>

    <div class="box">

    <h3>Клиент</h3>
    <p>{client}</p>

    <h3>Задача</h3>
    <p>{task}</p>

    <p>Дата: {date}</p>

    </div>

    <br>

    <a class="btn" href="/accept/{proposal_id}">
        Принять предложение
    </a>

    </body>
    </html>
    """

    return html

@app.get("/accept/{proposal_id}", response_class=HTMLResponse)
def accept_proposal(proposal_id: int):

    html = f"""
    <html>

    <body style="font-family:Arial; text-align:center; padding:100px">

    <h1>Спасибо!</h1>

    <p>Вы приняли коммерческое предложение.</p>

    <p>Менеджер свяжется с вами.</p>

    </body>

    </html>
    """

    return html
