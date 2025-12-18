import sqlite3
import sqlite_vec
import os
from typing import List, Generator
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "scribe.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Load the sqlite-vec extension
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                tags TEXT, -- JSON string of tags
                note_type TEXT DEFAULT 'Quick Thought',
                metadata TEXT DEFAULT '{}', -- JSON string of metadata
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: Add note_type and metadata if they don't exist
        cursor.execute("PRAGMA table_info(notes)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'note_type' not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN note_type TEXT DEFAULT 'Quick Thought'")
        if 'metadata' not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN metadata TEXT DEFAULT '{}'")
        
        # Migration: Remove summary column if it exists
        if 'summary' in columns:
            cursor.execute("ALTER TABLE notes DROP COLUMN summary")
            
        # Migration: Remove audio_path column if it exists
        if 'audio_path' in columns:
            cursor.execute("ALTER TABLE notes DROP COLUMN audio_path")
        
        # Create virtual table for vector search (sqlite-vec)
        # dimension should match all-MiniLM-L6-v2 which is 384
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_notes USING vec0(
                id INTEGER PRIMARY KEY,
                embedding FLOAT[384]
            )
        """)
        
        # Create settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        # Set default LLM model and URL if not exists
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('llm_model', 'llama3')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ollama_url', 'http://localhost:11434')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ollama_api_key', '')")
        
        conn.commit()

if __name__ == "__main__":
    init_db()
