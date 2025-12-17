import sqlite3
import sqlite_vec
import os
from typing import List

DB_PATH = os.getenv("DB_PATH", "scribe.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Load the sqlite-vec extension
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT NOT NULL,
            summary TEXT,
            tags TEXT, -- JSON string of tags
            audio_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create virtual table for vector search (sqlite-vec)
    # dimension should match all-MiniLM-L6-v2 which is 384
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_notes USING vec0(
            id INTEGER PRIMARY KEY,
            embedding FLOAT[384]
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

