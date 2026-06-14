"""Quét thư mục và thu thập file media theo cấu hình."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.constants import MEDIA_EXTENSIONS
from src.utils.logging_config import get_logger

logger = get_logger("scanner")

# Re-export để tương thích ngược.
DEFAULT_MEDIA_EXTENSIONS = set(MEDIA_EXTENSIONS)


@dataclass(slots=True, frozen=True)
class MediaFileEntry:
    """File media kèm kích thước (lấy một lần khi quét)."""

    path: Path
    size: int


class MediaFileScanner:
    """Lấy danh sách file media trong thư mục."""

    def __init__(self, media_extensions: Iterable[str] | None = None) -> None:
        self.media_extensions = {ext.lower() for ext in (media_extensions or MEDIA_EXTENSIONS)}

    def scan_entries(self, root: Path) -> list[MediaFileEntry]:
        """Quét đệ quy bằng scandir, trả về path và size trong một lần duyệt."""

        if not root.is_dir():
            raise NotADirectoryError(f"Không phải thư mục: {root}")

        results: list[MediaFileEntry] = []
        stack: list[Path] = [root.resolve()]

        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            suffix = Path(entry.name).suffix.lower()
                            if suffix not in self.media_extensions:
                                continue
                            stat = entry.stat(follow_symlinks=False)
                            results.append(MediaFileEntry(path=Path(entry.path), size=stat.st_size))
                        except OSError as exc:
                            logger.debug("Bỏ qua mục %s: %s", entry.path, exc)
            except OSError as exc:
                logger.warning("Không quét được thư mục %s: %s", current, exc)

        logger.debug("Quét %s: tìm thấy %s file media.", root, len(results))
        return results

    def scan_entries_multi(self, roots: list[Path]) -> list[MediaFileEntry]:
        """Quét nhiều thư mục/ổ đĩa, loại trùng path."""

        seen: set[str] = set()
        results: list[MediaFileEntry] = []
        for root in roots:
            if not root.is_dir():
                logger.warning("Bỏ qua root không phải thư mục: %s", root)
                continue
            try:
                entries = self.scan_entries(root)
            except NotADirectoryError:
                continue
            for entry in entries:
                key = str(entry.path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                results.append(entry)
        logger.info("Quét %s root: tổng %s file media (deduped).", len(roots), len(results))
        return results

    def scan(self, root: Path) -> list[Path]:
        """Quét đệ quy và trả về các file media hợp lệ."""

        return [entry.path for entry in self.scan_entries(root)]

    def scan_multi(self, roots: list[Path]) -> list[Path]:
        """Quét nhiều root và trả về path."""

        return [entry.path for entry in self.scan_entries_multi(roots)]
