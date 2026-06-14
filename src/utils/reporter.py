"""Xuất báo cáo kết quả."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from src.models.serializers import serialize_dataclass
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger("reporter")

# Re-export public API.
__all__ = ["ReportWriter", "setup_logging"]


class ReportWriter:
    """Ghi báo cáo CSV đơn giản."""

    def write_csv(self, path: Path, rows: Iterable[dict[str, Any]]) -> None:
        rows = list(rows)
        if not rows:
            path.write_text("", encoding="utf-8")
            logger.info("Đã ghi file CSV rỗng: %s", path)
            return

        try:
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            logger.info("Đã ghi %s dòng vào %s", len(rows), path)
        except OSError as exc:
            logger.error("Không ghi được CSV %s: %s", path, exc)
            raise

    def serialize_dataclass(self, obj: Any) -> dict[str, Any]:
        """Chuyển dataclass sang dict để xuất báo cáo."""

        return serialize_dataclass(obj)
