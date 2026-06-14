"""Parse và validate danh sách đường dẫn quét."""

from __future__ import annotations

import os
import string
import sys
from pathlib import Path

_PATH_SEPARATORS = (";", "|", "\n")


def list_windows_drives() -> list[Path]:
    """Liệt kê ổ đĩa Windows (C:\\, D:\\, ...)."""

    if sys.platform != "win32":
        return []
    try:
        import ctypes

        bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
        drives: list[Path] = []
        for index, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << index):
                drives.append(Path(f"{letter}:\\"))
        return drives
    except OSError:
        return []


def parse_scan_paths(text: str) -> list[Path]:
    """Tách chuỗi thành danh sách Path (hỗ trợ ; | newline)."""

    if not text or not text.strip():
        return []
    normalized = text
    for sep in _PATH_SEPARATORS[1:]:
        normalized = normalized.replace(sep, _PATH_SEPARATORS[0])
    parts = [part.strip().strip('"').strip("'") for part in normalized.split(_PATH_SEPARATORS[0])]
    return [Path(part).expanduser() for part in parts if part]


def format_scan_paths(paths: list[Path]) -> str:
    """Ghép danh sách path thành chuỗi hiển thị."""

    return "; ".join(str(path) for path in paths)


def validate_scan_roots(paths: list[Path]) -> tuple[list[Path], list[str]]:
    """Lọc root hợp lệ (thư mục hoặc ổ đĩa); trả (valid, errors)."""

    valid: list[Path] = []
    errors: list[str] = []
    seen: set[str] = set()

    for raw in paths:
        try:
            resolved = raw.resolve()
        except OSError:
            errors.append(f"Invalid path: {raw}")
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_dir():
            valid.append(resolved)
        else:
            errors.append(f"Not a folder or drive: {raw}")
    return valid, errors


def merge_scan_paths(existing: list[Path], new_paths: list[Path]) -> list[Path]:
    """Gộp path mới vào danh sách, loại trùng."""

    seen = {str(path.resolve()) for path in existing}
    merged = list(existing)
    for path in new_paths:
        try:
            key = str(path.resolve())
        except OSError:
            continue
        if key not in seen and path.exists():
            seen.add(key)
            merged.append(path.resolve())
    return merged
