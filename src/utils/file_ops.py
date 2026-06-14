"""Thao tác hệ thống: mở, xoá, di chuyển file."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import tempfile
import webbrowser
from collections.abc import Callable
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("file_ops")

# WinError 5 = Access denied, 32 = File in use (sharing violation)
_WINDOWS_LOCKED_ERRORS = {5, 32}


def open_path(path: Path) -> None:
    """Mở file hoặc thư mục bằng ứng dụng mặc định của hệ điều hành."""

    target = path.resolve()
    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
    elif shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", str(target)])
    elif shutil.which("open"):
        subprocess.Popen(["open", str(target)])
    else:
        webbrowser.open(target.as_uri())
    logger.info("Đã mở: %s", target)


def describe_delete_error(path: Path, exc: BaseException) -> str:
    """Chuyển lỗi xoá file sang thông báo dễ hiểu cho người dùng."""

    if isinstance(exc, OSError):
        winerror = getattr(exc, "winerror", None)
        if winerror in _WINDOWS_LOCKED_ERRORS or isinstance(exc, PermissionError):
            return (
                f"Không xoá được '{path.name}': không có quyền truy cập hoặc file đang bị khóa. "
                "Thử chạy ứng dụng với quyền quản trị viên, hoặc kiểm tra quyền ghi trên ổ đĩa chứa file."
            )
    return f"{path}: {exc}"


def _as_os_error(exc: BaseException, target: Path) -> OSError:
    """Chuyển mọi lỗi xoá file sang OSError để xử lý thống nhất."""

    if isinstance(exc, OSError):
        return exc
    if isinstance(exc, subprocess.CalledProcessError):
        detail = (exc.stderr or exc.stdout or "").strip()
        message = detail or f"Lệnh xoá thất bại (exit {exc.returncode})"
        return OSError(message)
    return OSError(str(exc))


def _ensure_deleted(target: Path) -> None:
    """Xác minh file đã bị xoá khỏi đĩa."""

    if target.exists():
        raise PermissionError(f"File vẫn còn sau khi xoá: {target}")


def _windows_extended_path(path: Path) -> str:
    """Chuyển sang extended path để Windows xử lý tên file đặc biệt."""

    text = str(path.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text


def _reset_windows_permissions(target: Path) -> None:
    """Lấy quyền sở hữu và cấp full control trước khi xoá (hữu ích trên ổ ngoài)."""

    if os.name != "nt":
        return

    path_str = str(target)
    subprocess.run(["takeown", "/f", path_str, "/a"], check=False, capture_output=True, text=True)
    username = os.environ.get("USERNAME", "")
    if username:
        subprocess.run(["icacls", path_str, "/grant", f"{username}:(F)"], check=False, capture_output=True, text=True)
    subprocess.run(["icacls", path_str, "/grant", "Administrators:(F)"], check=False, capture_output=True, text=True)


def _clear_windows_attributes(target: Path) -> None:
    """Gỡ thuộc tính read-only/hidden/system và reset quyền trước khi xoá."""

    if os.name != "nt":
        try:
            os.chmod(target, 0o666)
        except OSError as exc:
            logger.debug("Không đổi được quyền file %s: %s", target, exc)
        return

    _reset_windows_permissions(target)
    try:
        subprocess.run(["attrib", "-R", "-H", "-S", str(target)], check=False, capture_output=True)
    except OSError as exc:
        logger.debug("Không chạy được attrib cho %s: %s", target, exc)
    try:
        os.chmod(target, 0o666)
    except OSError as exc:
        logger.debug("Không đổi được quyền file %s: %s", target, exc)


def _win32_delete(target: Path) -> None:
    """Xoá file qua Win32 API — xử lý tốt tên có dấu nháy đơn và khoảng trắng."""

    extended = _windows_extended_path(target)
    if ctypes.windll.kernel32.DeleteFileW(extended) == 0:  # type: ignore[attr-defined]
        raise ctypes.WinError()  # type: ignore[attr-defined]


def _powershell_remove(target: Path) -> None:
    """Xoá file bằng PowerShell, hỗ trợ tên có dấu nháy đơn và khoảng trắng."""

    literal = str(target).replace("'", "''")
    script = f"Remove-Item -LiteralPath '{literal}' -Force -ErrorAction Stop"
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise OSError(detail or f"PowerShell Remove-Item thất bại (exit {completed.returncode})")


def _cmd_delete(target: Path) -> None:
    """Xoá file qua cmd — không thêm quote thừa vì subprocess truyền arg trực tiếp."""

    completed = subprocess.run(
        ["cmd", "/c", "del", "/f", "/q", str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise OSError(detail or f"cmd del thất bại (exit {completed.returncode})")


def force_delete_file(path: Path) -> None:
    """Xoá file, thử nhiều phương pháp trên Windows nếu bị từ chối quyền."""

    target = path.resolve()
    if not target.exists():
        logger.debug("File đã không còn, bỏ qua xoá: %s", target)
        return
    if not target.is_file():
        raise OSError(f"Không phải file thường, không xoá: {target}")

    last_error: OSError | None = None

    def _try_unlink(file_path: Path) -> None:
        file_path.unlink()
        _ensure_deleted(file_path)

    def _try_after_clear_attributes() -> None:
        _clear_windows_attributes(target)
        _try_unlink(target)

    def _try_extended_path_delete() -> None:
        _clear_windows_attributes(target)
        _try_unlink(Path(_windows_extended_path(target)))

    def _try_win32_delete() -> None:
        _clear_windows_attributes(target)
        _win32_delete(target)
        _ensure_deleted(target)

    def _try_powershell_delete() -> None:
        _clear_windows_attributes(target)
        _powershell_remove(target)
        _ensure_deleted(target)

    def _try_cmd_delete() -> None:
        _clear_windows_attributes(target)
        _cmd_delete(target)
        _ensure_deleted(target)

    def _try_move_to_temp_and_delete() -> None:
        _clear_windows_attributes(target)
        temp_path = Path(tempfile.gettempdir()) / f"mediatool_{target.name}"
        if temp_path.exists():
            temp_path.unlink()
        shutil.move(str(target), str(temp_path))
        temp_path.unlink(missing_ok=True)
        _ensure_deleted(target)

    attempts: list[tuple[str, Callable[[], None]]] = [
        ("unlink", lambda: _try_unlink(target)),
        ("chmod+unlink", _try_after_clear_attributes),
    ]
    if os.name == "nt":
        attempts.extend(
            [
                ("move temp+delete", _try_move_to_temp_and_delete),
                ("extended path", _try_extended_path_delete),
                ("win32 DeleteFileW", _try_win32_delete),
                ("powershell", _try_powershell_delete),
                ("cmd del", _try_cmd_delete),
            ]
        )

    for method_name, attempt in attempts:
        try:
            attempt()
            logger.info("Đã xoá file (%s): %s", method_name, target)
            return
        except Exception as exc:  # noqa: BLE001 — thu mọi lỗi để thử phương pháp kế tiếp
            last_error = _as_os_error(exc, target)
            logger.debug("Xoá thất bại [%s] %s: %s", method_name, target, last_error)

    if last_error is None:
        raise OSError(f"Không xoá được file: {target}")
    raise OSError(describe_delete_error(target, last_error)) from last_error


def move_file_safe(source: Path, destination_dir: Path) -> Path:
    """Di chuyển file vào thư mục đích, tránh ghi đè tên trùng."""

    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / source.name
    if target.exists():
        target = destination_dir / f"{source.stem}_{source.stat().st_size}{source.suffix}"
    shutil.move(str(source), str(target))
    logger.info("Đã di chuyển %s -> %s", source, target)
    return target


def delete_paths(paths: list[Path]) -> tuple[list[Path], list[str]]:
    """Xoá nhiều file, trả về (danh sách đã xoá, danh sách lỗi)."""

    deleted_paths: list[Path] = []
    errors: list[str] = []
    for path in paths:
        try:
            resolved = path.resolve()
            force_delete_file(resolved)
            deleted_paths.append(resolved)
        except OSError as exc:
            message = describe_delete_error(path, exc)
            errors.append(message)
            logger.error("Không xoá được file: %s", message)
    return deleted_paths, errors


def move_paths(sources: list[Path], destination_dir: Path) -> tuple[int, list[str]]:
    """Di chuyển nhiều file, trả về (số thành công, danh sách lỗi)."""

    moved = 0
    errors: list[str] = []
    for source in sources:
        try:
            move_file_safe(source, destination_dir)
            moved += 1
        except OSError as exc:
            message = f"{source}: {exc}"
            errors.append(message)
            logger.error("Không di chuyển được file: %s", message)
    return moved, errors
