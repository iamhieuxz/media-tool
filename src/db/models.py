"""Dataclass models cho SQLite persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from src.core.hash_engine import HashLevel


@dataclass
class AppSettings:
    """Cài đặt ứng dụng — lưu trong SQLite."""

    hash_level: int = int(HashLevel.EXACT_SHA256)
    similarity_threshold: float = 95.0
    worker_count: int = 0  # 0 = auto
    theme: str = "dark"
    language: str = "vi"
    auto_save: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        return cls(
            hash_level=int(data.get("hash_level", int(HashLevel.EXACT_SHA256))),
            similarity_threshold=float(data.get("similarity_threshold", 95.0)),
            worker_count=int(data.get("worker_count", 0)),
            theme=str(data.get("theme", "dark")),
            language=str(data.get("language", "vi")),
            auto_save=bool(data.get("auto_save", True)),
        )


@dataclass
class ScanHistoryEntry:
    """Một bản ghi lịch sử quét."""

    id: int
    started_at: str
    finished_at: str | None
    root_paths: list[str]
    total_files: int
    duplicate_count: int
    corrupted_count: int
    recoverable_bytes: int
    status: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> ScanHistoryEntry:
        paths_raw = row.get("root_paths", "[]")
        try:
            paths = json.loads(paths_raw) if isinstance(paths_raw, str) else paths_raw
        except json.JSONDecodeError:
            paths = []
        return cls(
            id=int(row["id"]),
            started_at=str(row["started_at"]),
            finished_at=row.get("finished_at"),
            root_paths=paths,
            total_files=int(row.get("total_files") or 0),
            duplicate_count=int(row.get("duplicate_count") or 0),
            corrupted_count=int(row.get("corrupted_count") or 0),
            recoverable_bytes=int(row.get("recoverable_bytes") or 0),
            status=str(row.get("status") or "unknown"),
        )
