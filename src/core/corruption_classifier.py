"""Phân loại mức độ hỏng file media — mở rộng MediaChecker."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

from src.core.checker import MediaCheckResult, MediaChecker
from src.utils.logging_config import get_logger

logger = get_logger("corruption_classifier")


class CorruptionSeverity(enum.StrEnum):
    """Mức độ lỗi file."""

    VALID = "valid"
    MINOR = "minor"
    MAJOR = "major"
    UNREADABLE = "unreadable"


@dataclass(slots=True)
class ClassifiedMediaResult:
    """Kết quả kiểm tra kèm phân loại mức độ lỗi."""

    path: Path
    is_valid: bool
    media_type: str
    error: str | None
    severity: CorruptionSeverity
    resolution: str = ""
    width: int = 0
    height: int = 0
    duration_sec: float = 0.0
    fps: float = 0.0
    codec: str = ""


def classify_error(error: str | None, media_type: str) -> CorruptionSeverity:
    """Phân loại lỗi dựa trên thông báo (fallback)."""

    if error is None:
        return CorruptionSeverity.VALID
    lower = error.lower()
    if any(k in lower for k in ("cannot identify", "truncated", "corrupt", "damaged", "header", "unreadable", "cannot read")):
        return CorruptionSeverity.UNREADABLE
    if any(k in lower for k in ("permission", "access", "thiếu thư viện", "ffprobe", "opencv cannot")):
        return CorruptionSeverity.MAJOR
    return CorruptionSeverity.MINOR


class CorruptionClassifier:
    """Bọc MediaChecker và thêm phân loại mức độ lỗi."""

    def __init__(self, checker: MediaChecker | None = None) -> None:
        self.checker = checker or MediaChecker()

    def classify(self, path: Path) -> ClassifiedMediaResult:
        result = self.checker.check(path)
        try:
            severity = CorruptionSeverity(result.severity)
        except ValueError:
            severity = (
                CorruptionSeverity.VALID
                if result.is_valid
                else classify_error(result.error, result.media_type)
            )
        return ClassifiedMediaResult(
            path=result.path,
            is_valid=result.is_valid,
            media_type=result.media_type,
            error=result.error,
            severity=severity,
            resolution=result.resolution,
            width=result.width,
            height=result.height,
            duration_sec=result.duration_sec,
            fps=result.fps,
            codec=result.codec,
        )

    @staticmethod
    def to_check_result(classified: ClassifiedMediaResult) -> MediaCheckResult:
        return MediaCheckResult(
            path=classified.path,
            is_valid=classified.is_valid,
            media_type=classified.media_type,
            error=classified.error,
            severity=classified.severity,
            resolution=classified.resolution,
            width=classified.width,
            height=classified.height,
            duration_sec=classified.duration_sec,
            fps=classified.fps,
            codec=classified.codec,
        )
