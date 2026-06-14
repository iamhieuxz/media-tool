"""Dịch vụ quét và kiểm tra file media lỗi."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from src.core.checker import MediaCheckResult, MediaChecker
from src.models.serializers import invalid_results_to_rows
from src.utils.concurrency import io_worker_count
from src.utils.file_handler import MediaFileEntry, MediaFileScanner
from src.utils.logging_config import get_logger

logger = get_logger("media_inspector")


class MediaInspectorService:
    """Điều phối quét thư mục và kiểm tra file lỗi."""

    def __init__(
        self,
        scanner: MediaFileScanner | None = None,
        checker: MediaChecker | None = None,
        worker_count: int = 0,
    ) -> None:
        self.scanner = scanner or MediaFileScanner()
        self.checker = checker or MediaChecker()
        self.worker_count = worker_count

    def _workers(self, total: int) -> int:
        return min(io_worker_count(self.worker_count), total) if total else 1

    def scan_entries(self, root: Path) -> list[MediaFileEntry]:
        """Quét và trả về danh sách file media kèm kích thước."""

        entries = self.scanner.scan_entries(root)
        logger.info("Quét thư mục %s: tìm thấy %s file media.", root, len(entries))
        return entries

    def scan_entries_multi(self, roots: list[Path]) -> list[MediaFileEntry]:
        """Quét nhiều thư mục/ổ đĩa."""

        entries = self.scanner.scan_entries_multi(roots)
        logger.info("Quét %s root: tìm thấy %s file media.", len(roots), len(entries))
        return entries

    def scan_files(self, root: Path) -> list[Path]:
        """Quét và trả về danh sách file media."""

        return [entry.path for entry in self.scan_entries(root)]

    def scan_files_multi(self, roots: list[Path]) -> tuple[list[Path], dict[Path, int]]:
        """Quét nhiều root, trả về path và map kích thước."""

        entries = self.scan_entries_multi(roots)
        sizes = {entry.path: entry.size for entry in entries}
        return [entry.path for entry in entries], sizes

    def scan_files_with_sizes(self, root: Path) -> tuple[list[Path], dict[Path, int]]:
        """Quét một lần, trả về path và map kích thước."""

        entries = self.scan_entries(root)
        sizes = {entry.path: entry.size for entry in entries}
        return [entry.path for entry in entries], sizes

    def check_files(
        self,
        files: list[Path],
        progress_callback: Callable[[int, int], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> list[MediaCheckResult]:
        """Kiểm tra file song song và trả về kết quả theo thứ tự gốc."""

        total = len(files)
        if total == 0:
            return []

        if total == 1:
            result = self.checker.check(files[0])
            if progress_callback is not None:
                progress_callback(1, 1)
            return [result]

        results: list[MediaCheckResult | None] = [None] * total
        completed = 0
        workers = self._workers(total)
        stopped = False

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="check") as executor:
            future_to_index = {
                executor.submit(self.checker.check, path): index for index, path in enumerate(files)
            }
            for future in as_completed(future_to_index):
                if should_stop is not None and should_stop():
                    stopped = True
                    for pending in future_to_index:
                        pending.cancel()
                    break
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as exc:  # noqa: BLE001 — giữ luồng xử lý ổn định
                    logger.warning("Lỗi khi kiểm tra %s: %s", files[index], exc)
                    results[index] = MediaCheckResult(
                        path=files[index],
                        is_valid=False,
                        media_type="không xác định",
                        error=str(exc),
                    )
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, total)

        if stopped:
            return [result for result in results if result is not None]
        return [result for result in results if result is not None]

    def scan_invalid_files(
        self,
        root: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Path], list[MediaCheckResult], list[dict[str, str]]]:
        """Quét thư mục, kiểm tra lỗi và trả về (files, results, invalid_rows)."""

        files = self.scan_files(root)
        results = self.check_files(files, progress_callback=progress_callback)
        invalid_rows = invalid_results_to_rows(results)
        logger.info(
            "Kiểm tra lỗi hoàn tất: %s file lỗi / %s file đã quét.",
            len(invalid_rows),
            len(files),
        )
        return files, results, invalid_rows
