"""Gói khởi tạo cho công cụ kiểm tra media và gỡ trùng lặp."""

from .core.checker import MediaChecker, MediaCheckResult
from .core.deduplicator import DuplicateFinder, DuplicateResult
from .utils.file_handler import MediaFileScanner
from .utils.reporter import ReportWriter, setup_logging

__all__ = [
    "MediaChecker",
    "MediaCheckResult",
    "DuplicateFinder",
    "DuplicateResult",
    "MediaFileScanner",
    "ReportWriter",
    "setup_logging",
]
