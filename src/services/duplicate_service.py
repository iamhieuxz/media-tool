"""Dịch vụ tìm file trùng lặp."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.core.deduplicator import DuplicateFinder, DuplicateResult
from src.core.hash_engine import HashLevel
from src.db.database import Database
from src.models.serializers import duplicate_groups_to_rows
from src.services.media_inspector import MediaInspectorService
from src.utils.logging_config import get_logger

logger = get_logger("duplicate_service")


class DuplicateService:
    """Điều phối quét thư mục và tìm file trùng lặp."""

    def __init__(
        self,
        inspector: MediaInspectorService | None = None,
        finder: DuplicateFinder | None = None,
        hash_level: HashLevel = HashLevel.EXACT_SHA256,
        similarity_threshold: float = 95.0,
        db: Database | None = None,
        worker_count: int = 0,
    ) -> None:
        self.inspector = inspector or MediaInspectorService(worker_count=worker_count)
        self.db = db
        self.hash_level = hash_level
        self.similarity_threshold = similarity_threshold
        self.worker_count = worker_count
        self.finder = finder or self._build_finder()

    def _build_finder(self) -> DuplicateFinder:
        return DuplicateFinder(
            hash_level=self.hash_level,
            similarity_threshold=self.similarity_threshold,
            db=self.db,
            worker_count=self.worker_count,
        )

    def configure(
        self,
        *,
        hash_level: HashLevel | None = None,
        similarity_threshold: float | None = None,
        worker_count: int | None = None,
    ) -> None:
        """Cập nhật cấu hình và rebuild finder."""

        if hash_level is not None:
            self.hash_level = hash_level
        if similarity_threshold is not None:
            self.similarity_threshold = similarity_threshold
        if worker_count is not None:
            self.worker_count = worker_count
            self.inspector.worker_count = worker_count
        self.finder = self._build_finder()

    def find_duplicates_in_folder(
        self,
        root: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Path], list[DuplicateResult], list[dict[str, object]]]:
        """Quét thư mục, tìm trùng lặp và trả về (files, groups, duplicate_rows)."""

        files = self.inspector.scan_files(root)
        groups = self.finder.find_duplicates(files, progress_callback=progress_callback)
        duplicate_rows = duplicate_groups_to_rows(groups)
        logger.info(
            "Tìm trùng lặp hoàn tất: %s nhóm / %s file đã quét.",
            len(groups),
            len(files),
        )
        return files, groups, duplicate_rows

    def find_duplicates_in_roots(
        self,
        roots: list[Path],
        progress_callback: Callable[[int, int], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> tuple[list[Path], dict[Path, int], list[DuplicateResult]]:
        """Quét nhiều root và tìm trùng lặp."""

        files, sizes = self.inspector.scan_files_multi(roots)
        groups = self.finder.find_duplicates(
            files,
            progress_callback=progress_callback,
            should_stop=should_stop,
            sizes=sizes,
        )
        logger.info(
            "Tìm trùng lặp (%s root) hoàn tất: %s nhóm / %s file.",
            len(roots),
            len(groups),
            len(files),
        )
        return files, sizes, groups
