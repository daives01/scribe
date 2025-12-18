from typing import Any, Optional
from app.database import get_db

class SettingsRepository:
    def get(self, key: str, default: Any = None) -> Any:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set(self, key: str, value: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, value))
            conn.commit()

settings_repository = SettingsRepository()
