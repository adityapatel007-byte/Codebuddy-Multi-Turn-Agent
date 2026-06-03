"""
Chat Persistence Layer (SQLite)

Stores conversation sessions and messages in a local SQLite database.
Each session has a title, timestamp, and a list of messages.
Messages store role, content, and metadata (tool calls, etc.)
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional


DB_PATH = os.getenv("DB_PATH", "codebuddy_chat.db")


class ChatDatabase:
    """Manages persistent chat storage with SQLite."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()

    # -----------------------------------------
    # Session CRUD
    # -----------------------------------------

    def create_session(self, title: str = "New Chat") -> int:
        """Create a new chat session. Returns the session ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO sessions (title) VALUES (?)", (title,)
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def get_session(self, session_id: int) -> Optional[dict]:
        """Get a session by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions, newest first."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_session_title(self, session_id: int, title: str):
        """Update a session's title."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, session_id),
        )
        conn.commit()
        conn.close()

    def delete_session(self, session_id: int):
        """Delete a session and all its messages."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

    # -----------------------------------------
    # Message CRUD
    # -----------------------------------------

    def add_message(self, session_id: int, role: str, content: str, metadata: dict = None):
        """Add a message to a session."""
        conn = self._get_conn()
        meta_json = json.dumps(metadata) if metadata else None
        conn.execute(
            "INSERT INTO messages (session_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (session_id, role, content, meta_json),
        )
        # Update session timestamp
        conn.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )
        conn.commit()
        conn.close()

    def get_messages(self, session_id: int) -> list[dict]:
        """Get all messages for a session, in chronological order."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        conn.close()

        messages = []
        for row in rows:
            msg = {
                "role": row["role"],
                "content": row["content"],
            }
            if row["metadata"]:
                msg["metadata"] = json.loads(row["metadata"])
            messages.append(msg)

        return messages

    def clear_messages(self, session_id: int):
        """Delete all messages in a session."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    # -----------------------------------------
    # Utilities
    # -----------------------------------------

    def auto_title(self, session_id: int, first_message: str):
        """
        Generate a session title from the first user message.
        Truncates to 40 chars for clean display.
        """
        title = first_message.strip()[:40]
        if len(first_message.strip()) > 40:
            title += "..."
        self.update_session_title(session_id, title)

    def get_session_count(self) -> int:
        """Return total number of sessions."""
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
        return count
