"""Điểm chạy CLI hoặc GUI cho bộ công cụ kiểm kê media."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.constants import APP_TITLE, DUPLICATE_MEDIA_CSV, INVALID_MEDIA_CSV
from src.gui import launch as launch_gui
from src.models.serializers import duplicate_groups_to_rows
from src.services.duplicate_service import DuplicateService
from src.services.media_inspector import MediaInspectorService
from src.utils.admin import ensure_admin_on_windows
from src.utils.logging_config import setup_logging
from src.utils.reporter import ReportWriter


def run_cli(roots: list[Path]) -> int:
    """Chạy quét media, kiểm tra lỗi và phát hiện trùng lặp."""

    logger = setup_logging()
    inspector = MediaInspectorService()
    duplicate_service = DuplicateService(inspector=inspector)
    reporter = ReportWriter()

    try:
        if len(roots) == 1:
            files, sizes = inspector.scan_files_with_sizes(roots[0])
        else:
            files, sizes = inspector.scan_files_multi(roots)
        check_results = inspector.check_files(files)
        duplicate_groups = duplicate_service.finder.find_duplicates(files, sizes=sizes)
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        logger.error("Quét thất bại: %s", exc)
        return 1

    invalid_rows = [reporter.serialize_dataclass(result) for result in check_results if not result.is_valid]
    duplicate_rows = duplicate_groups_to_rows(duplicate_groups)

    reporter.write_csv(Path(INVALID_MEDIA_CSV), invalid_rows)
    reporter.write_csv(Path(DUPLICATE_MEDIA_CSV), duplicate_rows)

    logger.info(
        "Hoàn tất kiểm tra. File lỗi: %s, nhóm trùng lặp: %s",
        len(invalid_rows),
        len(duplicate_groups),
    )
    return 0


def parse_args() -> argparse.Namespace:
    """Phân tích tham số dòng lệnh."""

    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Chạy chế độ dòng lệnh (CLI) thay vì giao diện đồ họa mặc định",
    )
    parser.add_argument(
        "--path",
        type=Path,
        nargs="*",
        default=None,
        help="Thư mục cần quét (có thể nhiều path) — chỉ dùng với --cli",
    )
    return parser.parse_args()


def _cli_roots(args: argparse.Namespace) -> list[Path]:
    if args.path:
        return list(args.path)
    return [Path.cwd()]


def main() -> int:
    """Điểm khởi chạy chính."""

    ensure_admin_on_windows()

    args = parse_args()
    if args.cli:
        return run_cli(_cli_roots(args))
    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
