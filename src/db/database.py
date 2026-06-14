"""SQLite persistence — scan history, hash cache, settings."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src.db.models import AppSettings, ScanHistoryEntry
from src.utils.logging_config import get_logger

logger = get_logger("database")

DEFAULT_DB_PATH = Path("data") / "media_scanner.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    root_paths      TEXT NOT NULL,
    total_files     INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0,
    corrupted_count INTEGER DEFAULT 0,
    recoverable_bytes INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS hash_cache (
    path        TEXT PRIMARY KEY,
    size        INTEGER NOT NULL,
    mtime       REAL NOT NULL,
    hash_value  TEXT NOT NULL,
    hash_level  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


class Database:
    """Wrapper SQLite cho Media Scanner Pro."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()
        logger.debug("Database schema sẵn sàng: %s", self.db_path)

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Settings ──────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.session() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def load_settings(self) -> AppSettings:
        raw = self.get_setting("app_settings", "")
        if not raw:
            return AppSettings()
        try:
            data = json.loads(raw)
            return AppSettings.from_dict(data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self.set_setting("app_settings", json.dumps(settings.to_dict()))

    # ── Scan History ──────────────────────────────────────

    def insert_scan(self, root_paths: list[str]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.session() as conn:
            cursor = conn.execute(
                "INSERT INTO scan_history (started_at, root_paths, status) VALUES (?, ?, 'running')",
                (now, json.dumps(root_paths)),
            )
            return int(cursor.lastrowid)

    def finish_scan(
        self,
        scan_id: int,
        *,
        total_files: int,
        duplicate_count: int,
        corrupted_count: int,
        recoverable_bytes: int,
        status: str = "completed",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.session() as conn:
            conn.execute(
                """UPDATE scan_history SET
                    finished_at = ?, total_files = ?, duplicate_count = ?,
                    corrupted_count = ?, recoverable_bytes = ?, status = ?
                WHERE id = ?""",
                (now, total_files, duplicate_count, corrupted_count, recoverable_bytes, status, scan_id),
            )

    def list_scans(self, limit: int = 20) -> list[ScanHistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM scan_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ScanHistoryEntry.from_row(dict(row)) for row in rows]

    # ── Hash Cache ────────────────────────────────────────

    def get_cached_hash(self, path: Path, size: int, mtime: float, hash_level: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT hash_value FROM hash_cache WHERE path = ? AND size = ? AND mtime = ? AND hash_level = ?",
                (str(path.resolve()), size, mtime, hash_level),
            ).fetchone()
        return row["hash_value"] if row else None

    def store_hash(self, path: Path, size: int, mtime: float, hash_value: str, hash_level: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.session() as conn:
            conn.execute(
                """INSERT INTO hash_cache (path, size, mtime, hash_value, hash_level, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(path) DO UPDATE SET
                       size = excluded.size, mtime = excluded.mtime,
                       hash_value = excluded.hash_value, hash_level = excluded.hash_level,
                       updated_at = excluded.updated_at""",
                (str(path.resolve()), size, mtime, hash_value, hash_level, now),
            )

    def clear_hash_cache(self) -> None:
        with self.session() as conn:
            conn.execute("DELETE FROM hash_cache")
