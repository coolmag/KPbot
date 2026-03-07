import sqlite3
import datetime
from pathlib import Path

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
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_proposal(user_id, client, task):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO proposals (user_id, client, task, created_at)
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        client,
        task,
        datetime.datetime.now().isoformat()
    ))

    proposal_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return proposal_id


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
