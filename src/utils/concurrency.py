"""Tiện ích điều phối luồng cho tác vụ I/O."""

from __future__ import annotations

import os


def io_worker_count(configured: int = 0) -> int:
    """Số worker cho tác vụ I/O song song (đọc file, hash, kiểm tra media)."""

    if configured > 0:
        return max(1, min(configured, 32))
    cpu = os.cpu_count() or 4
    return max(2, min(cpu * 2, 16))
