import sqlite3
import os

DB_NAME = "youtube_assistant.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Channels table
    c.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT,
            user_prompt TEXT
        )
    ''')

    # Videos table
    c.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            channel_id TEXT,
            title TEXT,
            summary TEXT,
            status TEXT,
            published_at TEXT,
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        )
    ''')

    # Keywords table
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            video_id TEXT,
            FOREIGN KEY(video_id) REFERENCES videos(id)
        )
    ''')

    conn.commit()
    conn.close()

def upsert_channel(channel_id, name, user_prompt):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO channels (id, name, user_prompt)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            user_prompt=excluded.user_prompt
    ''', (channel_id, name, user_prompt))
    conn.commit()
    conn.close()

def get_video(video_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_video(video_id, channel_id, title, published_at, status='new'):
    conn = get_connection()
    c = conn.cursor()
    # Using INSERT OR IGNORE to avoid errors if it already exists,
    # though we might want to update if it exists.
    # For now, if it exists, we assume we don't need to re-add it
    # unless we want to update the status.
    c.execute('''
        INSERT OR IGNORE INTO videos (id, channel_id, title, published_at, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (video_id, channel_id, title, published_at, status))
    conn.commit()
    conn.close()

def update_video_status(video_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE videos SET status = ? WHERE id = ?', (status, video_id))
    conn.commit()
    conn.close()

def update_video_summary(video_id, summary):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE videos SET summary = ? WHERE id = ?', (summary, video_id))
    conn.commit()
    conn.close()

def add_keyword(video_id, keyword):
    conn = get_connection()
    c = conn.cursor()
    # Check if keyword exists for this video to avoid duplicates if re-run
    c.execute('SELECT id FROM keywords WHERE video_id = ? AND keyword = ?', (video_id, keyword))
    if not c.fetchone():
        c.execute('INSERT INTO keywords (keyword, video_id) VALUES (?, ?)', (keyword, video_id))
    conn.commit()
    conn.close()

def get_keywords_for_video(video_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT keyword FROM keywords WHERE video_id = ?', (video_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]
