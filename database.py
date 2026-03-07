import sqlite3
import datetime
from pathlib import Path
import json
import os

# Если мы на Railway (есть переменная RAILWAY_ENVIRONMENT), используем папку /data
# Иначе (на локальном ПК) создаем файл прямо в папке проекта
if os.getenv("RAILWAY_ENVIRONMENT"):
    DB_PATH = Path("/data/proposals.db")
else:
    DB_PATH = Path("proposals.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Обновленная таблица предложений с версионированием
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        client TEXT,
        task TEXT,
        created_at TEXT,
        proposal_data TEXT,
        version INTEGER DEFAULT 1
    )
    """)
    
    # НОВАЯ ТАБЛИЦА: Система событий (Events)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proposal_id INTEGER,
        event_type TEXT, -- 'opened', 'scrolled', 'plan_clicked', 'ai_question', 'accepted'
        timestamp TEXT,
        metadata TEXT,   -- JSON с деталями (например, глубиной скролла или выбранным тарифом)
        FOREIGN KEY(proposal_id) REFERENCES proposals(id)
    )
    """)
    conn.commit()
    conn.close()

def log_event(proposal_id: str, event_type: str, metadata: dict = None):
    """Функция для записи любого действия клиента"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO events (proposal_id, event_type, timestamp, metadata)
    VALUES (?, ?, ?, ?)
    """, (
        proposal_id, 
        event_type, 
        datetime.datetime.now().isoformat(), 
        json.dumps(metadata) if metadata else "{}"
    ))
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
