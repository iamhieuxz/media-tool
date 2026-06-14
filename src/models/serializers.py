"""Chuyển đổi dataclass kết quả sang dict cho CSV và GUI."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.core.checker import MediaCheckResult
from src.core.deduplicator import DuplicateResult


def invalid_result_to_row(result: MediaCheckResult) -> dict[str, str]:
    """Chuyển kết quả kiểm tra lỗi sang dict cho CSV/GUI."""

    return {
        "path": str(result.path),
        "media_type": result.media_type,
        "error": result.error or "",
        "severity": str(result.severity),
        "resolution": result.resolution,
        "duration_sec": str(result.duration_sec),
        "fps": str(result.fps),
        "codec": result.codec,
    }


def invalid_results_to_rows(results: list[MediaCheckResult]) -> list[dict[str, str]]:
    """Lọc và chuyển các file không hợp lệ sang danh sách dict."""

    return [invalid_result_to_row(result) for result in results if not result.is_valid]


def duplicate_group_to_row(group: DuplicateResult) -> dict[str, object]:
    """Chuyển nhóm trùng lặp sang dict cho CSV/GUI."""

    return {
        "size": group.size,
        "hash_value": group.hash_value,
        "paths": [str(path) for path in group.paths],
        "match_type": group.match_type,
        "similarity": group.similarity,
        "path_similarities": dict(group.path_similarities),
    }


def duplicate_groups_to_rows(groups: list[DuplicateResult]) -> list[dict[str, object]]:
    """Chuyển danh sách nhóm trùng lặp sang dict."""

    return [duplicate_group_to_row(group) for group in groups]


def serialize_dataclass(obj: Any) -> dict[str, Any]:
    """Chuyển dataclass sang dict (tương thích ReportWriter.serialize_dataclass)."""

    return asdict(obj)
