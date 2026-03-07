import sqlite3
import datetime
from pathlib import Path
import json

DB_PATH = Path("proposals.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        client TEXT,
        task TEXT,
        created_at TEXT,
        proposal_data TEXT
    )
    """)
    conn.commit()
    conn.close()


def save_proposal(user_id, client, task):
    """Сохраняет первоначальную информацию о лиде и возвращает ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO proposals (user_id, client, task, created_at, proposal_data)
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        client,
        task,
        datetime.datetime.now().isoformat(),
        None  # proposal_data is initially empty
    ))
    proposal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return proposal_id

def update_proposal_with_data(proposal_id, proposal_data):
    """Обновляет запись в БД, добавляя полный JSON сгенерированного КП."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE proposals
    SET proposal_data = ?
    WHERE id = ?
    """, (
        json.dumps(proposal_data, ensure_ascii=False),
        proposal_id
    ))
    conn.commit()
    conn.close()


def get_user_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, client, created_at
    FROM proposals
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT 10
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM proposals")
    total = cursor.fetchone()[0]
    conn.close()
    return total

def get_proposal_data(proposal_id: str) -> dict | None:
    """Извлекает полный JSON предложения по его ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT proposal_data FROM proposals WHERE id = ?", (proposal_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return None
