"""Yêu cầu quyền quản trị viên trên Windows."""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("admin")


def is_admin() -> bool:
    """Kiểm tra tiến trình hiện tại có quyền quản trị viên không."""

    if sys.platform != "win32":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except OSError:
        return False


def _elevation_command_line() -> tuple[str, str]:
    """Tạo (executable, params) để khởi chạy lại với quyền admin."""

    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess.list2cmdline(sys.argv[1:])
        return executable, params

    executable = sys.executable
    script = str(Path(sys.argv[0]).resolve())
    params = subprocess.list2cmdline([script, *sys.argv[1:]])
    return executable, params


def ensure_admin_on_windows() -> None:
    """Khởi chạy lại với UAC nếu chưa có quyền quản trị viên (chỉ Windows)."""

    if sys.platform != "win32":
        return
    if is_admin():
        logger.debug("Đang chạy với quyền quản trị viên.")
        return

    executable, params = _elevation_command_line()
    logger.info("Đang yêu cầu quyền quản trị viên...")
    print("Công cụ Media cần quyền quản trị viên để xoá file. Vui lòng chấp nhận hộp thoại UAC.")

    result = ctypes.windll.shell32.ShellExecuteW(  # type: ignore[attr-defined]
        None,
        "runas",
        executable,
        params,
        None,
        1,
    )
    if result <= 32:
        print("Không thể nâng quyền quản trị viên. Hãy chạy lại terminal hoặc ứng dụng với quyền quản trị viên.")
        raise SystemExit(1)

    # Process cũ thoát; process mới (đã elevated) tiếp tục.
    raise SystemExit(0)
