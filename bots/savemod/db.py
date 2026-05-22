"""SQLite kesh: kelgan xabarlarni qisqa muddatga saqlaydi.

O'chirilgan/tahrirlangan xabar event'i kelganda biz keshdan eski matnni topamiz.
"""
from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    chat_id          INTEGER NOT NULL,
    msg_id           INTEGER NOT NULL,
    sender_id        INTEGER,
    sender_name      TEXT,
    sender_username  TEXT,
    text             TEXT,
    has_media        INTEGER NOT NULL DEFAULT 0,
    media_path       TEXT,
    media_type       TEXT,
    is_private       INTEGER NOT NULL DEFAULT 1,
    is_channel       INTEGER NOT NULL DEFAULT 0,
    created_at       INTEGER NOT NULL,
    PRIMARY KEY (chat_id, msg_id)
);
CREATE INDEX IF NOT EXISTS idx_msg_id ON messages(msg_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON messages(created_at);
"""


class Cache:
    def __init__(self, path: str | Path = "cache.db"):
        self.path = str(path)
        with closing(self._conn()) as c:
            c.executescript(SCHEMA)
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(
        self,
        *,
        chat_id: int,
        msg_id: int,
        sender_id: int | None,
        sender_name: str | None,
        sender_username: str | None,
        text: str | None,
        has_media: bool,
        media_path: str | None,
        media_type: str | None,
        is_private: bool,
        is_channel: bool = False,
    ) -> None:
        with closing(self._conn()) as c:
            c.execute(
                """
                INSERT OR REPLACE INTO messages
                (chat_id, msg_id, sender_id, sender_name, sender_username,
                 text, has_media, media_path, media_type, is_private, is_channel, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    msg_id,
                    sender_id,
                    sender_name,
                    sender_username,
                    text,
                    int(has_media),
                    media_path,
                    media_type,
                    int(is_private),
                    int(is_channel),
                    int(time.time()),
                ),
            )
            c.commit()

    def update_text(self, chat_id: int, msg_id: int, new_text: str | None) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "UPDATE messages SET text = ? WHERE chat_id = ? AND msg_id = ?",
                (new_text, chat_id, msg_id),
            )
            c.commit()

    def get(self, chat_id: int, msg_id: int) -> dict | None:
        with closing(self._conn()) as c:
            row = c.execute(
                "SELECT * FROM messages WHERE chat_id = ? AND msg_id = ?",
                (chat_id, msg_id),
            ).fetchone()
        return dict(row) if row else None

    def find_by_msg_id(self, msg_id: int) -> list[dict]:
        """chat_id noma'lum bo'lganda - msg_id bo'yicha qidirish."""
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT * FROM messages WHERE msg_id = ? ORDER BY created_at DESC",
                (msg_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, chat_id: int, msg_id: int) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "DELETE FROM messages WHERE chat_id = ? AND msg_id = ?",
                (chat_id, msg_id),
            )
            c.commit()

    def prune(self, older_than_hours: int) -> int:
        cutoff = int(time.time()) - older_than_hours * 3600
        with closing(self._conn()) as c:
            cur = c.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
            c.commit()
            return cur.rowcount
