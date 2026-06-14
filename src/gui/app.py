"""Ứng dụng Flet chính — Media Scanner Pro."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog

try:
    import flet as ft
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        "Thiếu thư viện 'flet'. Hãy cài đặt bằng: pip install -r requirements.txt"
    ) from exc

from src.constants import (
    DATA_DIR,
    DUPLICATE_MEDIA_CSV,
    INVALID_MEDIA_CSV,
    LOGS_DIR,
    QUARANTINE_DIR,
    UI_UPDATE_INTERVAL_SEC,
)
from src.core.hash_engine import HashLevel
from src.db import AppSettings, Database
from src.gui.components.footer import build_footer
from src.gui.components.header import build_header
from src.gui.components.log_panel import LogPanelControls, build_log_panel
from src.gui.components.preview_panel import PreviewControls, build_preview_panel
from src.gui.components.progress_section import ProgressControls, build_progress_section
from src.gui.components.result_tabs import (
    ResultRow,
    ResultTabsControls,
    build_result_tabs,
    rows_from_duplicates,
    rows_from_invalid,
)
from src.gui.components.scan_section import ScanSectionControls, build_scan_section
from src.gui.components.stat_cards import StatCardControls, build_stat_cards
from src.gui.dialogs import close_dialog, show_confirm_dialog
from src.gui.settings_dialog import show_settings_dialog
from src.gui.theme import AppTheme, apply_page_theme
from src.models.duplicate_groups import DuplicateGroupManager
from src.models.serializers import duplicate_group_to_row, invalid_result_to_row
from src.services.duplicate_service import DuplicateService
from src.services.media_inspector import MediaInspectorService
from src.utils.file_ops import delete_paths, describe_delete_error, force_delete_file, move_paths, open_path
from src.utils.logging_config import setup_logging
from src.utils.reporter import ReportWriter
from src.utils.scan_paths import (
    format_scan_paths,
    list_windows_drives,
    merge_scan_paths,
    parse_scan_paths,
    validate_scan_roots,
)
from src.utils.thumbnail_cache import ThumbnailCache
from src.utils.media_metadata import extract_metadata


def _format_bytes(num: int) -> str:
    if num >= 1_073_741_824:
        return f"{num / 1_073_741_824:.1f} GB"
    if num >= 1_048_576:
        return f"{num / 1_048_576:.1f} MB"
    if num >= 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num} B"


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    return f"{mins}:{secs:02d}"


class MediaScannerProApp:
    """Orchestrator GUI — Media Scanner Pro."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
        Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(QUARANTINE_DIR).mkdir(parents=True, exist_ok=True)
        log_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = setup_logging(Path(LOGS_DIR) / f"scan_{log_name}.log")

        self.db = Database()
        self.settings = self.db.load_settings()

        self.inspector = MediaInspectorService(worker_count=self.settings.worker_count)
        self.duplicate_service = DuplicateService(
            inspector=self.inspector,
            db=self.db,
            hash_level=HashLevel(self.settings.hash_level),
            similarity_threshold=self.settings.similarity_threshold,
            worker_count=self.settings.worker_count,
        )
        self.reporter = ReportWriter()
        self._thumb_cache = ThumbnailCache()
        self._scan_roots: list[Path] = []
        self._selected_row: ResultRow | None = None

        self.is_scanning = False
        self._is_paused = False
        self._scan_id = 0
        self._last_ui_update = 0.0
        self._last_status_message = ""

        # Scan metrics
        self._scan_start_time = 0.0
        self._files_processed = 0
        self._total_files = 0
        self._current_scan_db_id: int | None = None

        # Result data
        self.invalid_rows: list[dict[str, str]] = []
        self.duplicate_rows: list[dict[str, object]] = []
        self._all_scanned_files: list[Path] = []

        # UI components (built in build())
        self._header: object = None
        self._scan: ScanSectionControls | None = None
        self._progress: ProgressControls | None = None
        self._stats: StatCardControls | None = None
        self._results: ResultTabsControls | None = None
        self._preview: PreviewControls | None = None
        self._log: LogPanelControls | None = None
        self._footer: object = None

    def build(self) -> None:
        apply_page_theme(self.page)

        header = build_header(
            on_search_change=self._on_search_change,
            on_settings=self._open_settings,
            on_theme_toggle=self._toggle_theme,
        )
        scan = build_scan_section(
            on_browse=self._pick_folder,
            on_add_drive=self._pick_drive,
            on_clear_paths=self._clear_scan_paths,
            on_start=self._start_scan,
            on_pause=self._toggle_pause,
            on_stop=self._request_stop,
            on_refresh=self._refresh_results,
        )
        progress = build_progress_section()
        stats = build_stat_cards()
        results = build_result_tabs(
            on_preview=self._preview_selected,
            on_delete_selected=self._delete_selected,
            on_recycle_bin=self._quarantine_invalid_files,
        )
        results.set_on_row_select(self._on_row_selected)
        results.set_thumbnail_cache(self._thumb_cache)
        preview = build_preview_panel(
            on_fit=self._preview_fit,
            on_zoom_in=lambda _e: self._preview_zoom(0.25),
            on_zoom_out=lambda _e: self._preview_zoom(-0.25),
            on_compare=self._preview_compare,
        )
        preview.set_thumbnail_cache(self._thumb_cache)
        log_panel = build_log_panel(on_clear=self._clear_log)
        footer = build_footer(
            on_export=self._export_all,
            on_save_report=self._save_report,
            on_delete_selected=self._delete_selected,
            on_clean_duplicates=self._confirm_delete_duplicates,
            on_clean_corrupted=self._delete_all_invalid_files,
        )

        self._sync_path_field()

        self._header = header
        self._scan = scan
        self._progress = progress
        self._stats = stats
        self._results = results
        self._preview = preview
        self._log = log_panel
        self._footer = footer

        self.page.add(
            ft.Column(
                expand=True,
                spacing=10,
                controls=[
                    header.container,
                    ft.Row(
                        expand=True,
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=[
                            # ── Cột trái (~70%): quét, stats, bảng, footer ──
                            ft.Container(
                                expand=7,
                                content=ft.Column(
                                    expand=True,
                                    spacing=10,
                                    controls=[
                                        scan.container,
                                        progress.container,
                                        stats.row,
                                        ft.Container(expand=True, content=results.container),
                                        footer.container,
                                    ],
                                ),
                            ),
                            # ── Cột phải (~30%): preview + log ──
                            ft.Container(
                                expand=3,
                                width=320,
                                content=ft.Column(
                                    expand=True,
                                    spacing=10,
                                    controls=[
                                        preview.container,
                                        ft.Container(expand=True, content=log_panel.container),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            )
        )
        self._log_msg("Sẵn sàng — chọn thư mục và bắt đầu quét.", level="success")

    # ── UI helpers ────────────────────────────────────────

    def _ui(self, func, *args, **kwargs) -> None:
        if hasattr(self.page, "call_from_thread"):
            self.page.call_from_thread(func, *args, **kwargs)
        else:
            func(*args, **kwargs)

    def _request_page_update(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if force or now - self._last_ui_update >= UI_UPDATE_INTERVAL_SEC:
            self._last_ui_update = now
            self.page.update()

    def _log_msg(self, message: str, level: str = "info") -> None:
        log_fn = getattr(self.logger, level if level != "status" else "info", self.logger.info)
        log_fn(message)
        if self._log:
            self._log.append(message, level=level)  # type: ignore[arg-type]

    def _set_status(self, message: str) -> None:
        if message == self._last_status_message:
            return
        self._last_status_message = message
        self._log_msg(message, level="status")

    def _update_progress_ui(
        self,
        index: int,
        total: int,
        current_file: str = "",
    ) -> None:
        if not self._progress:
            return
        pct = index / max(total, 1)
        self._progress.progress_bar.value = pct
        self._progress.pct_label.value = f"Scan percentage ({int(pct * 100)}%)"
        if current_file:
            self._progress.current_file_label.value = f"Current file: {current_file}"

        elapsed = time.monotonic() - self._scan_start_time if self._scan_start_time else 0
        self._progress.elapsed_label.value = f"Elapsed: {_format_duration(elapsed)}"

        if index > 0 and elapsed > 0:
            speed = index / elapsed
            self._progress.speed_label.value = f"{speed:.1f} files/s"
            remaining = (total - index) / speed if speed > 0 else 0
            mins, secs = divmod(int(remaining), 60)
            self._progress.eta_label.value = f"Estimated remaining: {mins}:{secs:02d} min"
            if self._stats:
                self._stats.speed_value.value = f"{speed:.1f}/s"
        self._request_page_update()

    def _update_stats(self) -> None:
        if not self._stats:
            return
        total = len(self._all_scanned_files)
        dup_count = sum(max(len(g.get("paths", [])) - 1, 0) for g in self.duplicate_rows)
        corrupt_count = len(self.invalid_rows)
        recoverable = sum(
            int(g.get("size", 0) or 0) * max(len(g.get("paths", [])) - 1, 0)
            for g in self.duplicate_rows
        )

        self._stats.total_value.value = f"{total:,}"
        self._stats.duplicate_value.value = f"{dup_count:,}"
        self._stats.corrupted_value.value = f"{corrupt_count:,}"
        self._stats.recoverable_value.value = _format_bytes(recoverable)
        self._request_page_update()

    def _refresh_result_table(self) -> None:
        if not self._results:
            return
        dup_rows = rows_from_duplicates(self.duplicate_rows)
        err_rows = rows_from_invalid(self.invalid_rows)
        self._results.update_rows(dup_rows + err_rows)
        dup_deletable = DuplicateGroupManager.count_deletable(self.duplicate_rows)
        if self._results._delete_selected_btn:
            sel = len(self._results.selected_ids)
            self._results.update_selection_count(sel, dup_deletable)
        self._update_stats()

    # ── Event handlers ────────────────────────────────────

    def _on_search_change(self, event: ft.ControlEvent) -> None:
        if self._results:
            self._results.set_search_query(event.control.value or "")
            self._request_page_update(force=True)

    def _on_row_selected(self, row: ResultRow) -> None:
        self._selected_row = row
        if self._preview:
            path = Path(row.path)
            meta = extract_metadata(path) if path.exists() else None
            self._preview.show_file(
                path,
                size=row.size,
                resolution=row.resolution,
                metadata=meta,
            )
            self._request_page_update(force=True)

    def _preview_selected(self, _event: ft.ControlEvent) -> None:
        if not self._results:
            return
        selected = self._results.get_selected_rows()
        if selected:
            self._on_row_selected(selected[0])
        elif self._selected_row:
            self._on_row_selected(self._selected_row)
        else:
            self._set_status("Select a file to preview")

    def _preview_fit(self, _event: ft.ControlEvent) -> None:
        if self._preview:
            self._preview.set_fit_mode("contain")
            self.page.update()

    def _preview_zoom(self, delta: float) -> None:
        if self._preview:
            self._preview.zoom(delta)
            self.page.update()

    def _preview_compare(self, _event: ft.ControlEvent) -> None:
        if not self._preview or not self._selected_row or not self._results:
            self._set_status("Select a duplicate file to compare")
            return
        row = self._selected_row
        if row.group_id == "—":
            self._set_status("Compare is only available for duplicate groups")
            return
        siblings = [
            r for r in self._results.rows if r.group_id == row.group_id and r.path != row.path
        ]
        if not siblings:
            self._set_status("No sibling file in this duplicate group")
            return
        self._preview.set_compare(Path(row.path), Path(siblings[0].path))
        self.page.update()

    def _open_settings(self, _event: ft.ControlEvent) -> None:
        show_settings_dialog(self.page, self.settings, self._save_settings)

    def _apply_settings_to_services(self) -> None:
        """Đồng bộ settings vào inspector và duplicate finder."""

        self.inspector.worker_count = self.settings.worker_count
        self.duplicate_service.configure(
            hash_level=HashLevel(self.settings.hash_level),
            similarity_threshold=self.settings.similarity_threshold,
            worker_count=self.settings.worker_count,
        )

    def _sync_path_field(self) -> None:
        """Cập nhật text field và chips từ _scan_roots."""

        if not self._scan:
            return
        if self._scan_roots:
            self._scan.path_field.value = format_scan_paths(self._scan_roots)
        else:
            self._scan.path_field.value = ""
        show_chips = len(self._scan_roots) > 1
        self._scan.path_chips.visible = show_chips
        self._scan.path_chips.controls = [
            ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=AppTheme.RADIUS_SM,
                bgcolor=AppTheme.SURFACE_ELEVATED,
                border=ft.border.all(1, AppTheme.BORDER),
                content=ft.Text(str(path), size=10, color=AppTheme.TEXT_SECONDARY),
            )
            for path in self._scan_roots
        ] if show_chips else []

    def _parse_roots_from_field(self) -> list[Path]:
        text = self._scan.path_field.value if self._scan else ""
        return parse_scan_paths(text)

    def _get_valid_scan_roots(self) -> list[Path] | None:
        parsed_roots = self._parse_roots_from_field()
        if not parsed_roots:
            self._set_status("Please enter or choose at least one scan path")
            return None
        roots, errors = validate_scan_roots(parsed_roots)
        for err in errors:
            self._log_msg(err, level="warning")
        if not roots:
            self._set_status("No valid folder or drive selected")
            return None
        self._scan_roots = roots
        self._sync_path_field()
        return roots

    def _save_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.db.save_settings(settings)
        self._apply_settings_to_services()
        self._log_msg("Settings saved.", level="success")

    def _toggle_theme(self, _event: ft.ControlEvent) -> None:
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            if self._header:
                self._header.theme_toggle.icon = ft.icons.LIGHT_MODE  # type: ignore[union-attr]
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            if self._header:
                self._header.theme_toggle.icon = ft.icons.DARK_MODE  # type: ignore[union-attr]
        self.page.update()

    def _pick_folder(self, _event: ft.ControlEvent) -> None:
        folder = ""
        root = None
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            initial = str(self._scan_roots[0]) if self._scan_roots else str(Path.cwd())
            folder = filedialog.askdirectory(
                parent=root,
                title="Add folder to scan",
                initialdir=initial,
            )
        except tk.TclError as exc:
            self._log_msg(f"Cannot open folder picker: {exc}", level="error")
        finally:
            if root is not None:
                root.destroy()
        if folder:
            self._scan_roots = merge_scan_paths(self._scan_roots, [Path(folder)])
            self._sync_path_field()
            self._set_status(f"Added folder: {folder}")
            self.page.update()

    def _pick_drive(self, _event: ft.ControlEvent) -> None:
        drives = list_windows_drives()
        if not drives:
            self._log_msg("Drive picker is only available on Windows.", level="warning")
            return
        self._scan_roots = merge_scan_paths(self._scan_roots, drives)
        self._sync_path_field()
        self._set_status(f"Added {len(drives)} drive(s): {', '.join(str(d) for d in drives)}")
        self.page.update()

    def _clear_scan_paths(self, _event: ft.ControlEvent) -> None:
        self._scan_roots = []
        self._sync_path_field()
        self._log_msg("Scan paths cleared.", level="status")
        self.page.update()

    def _folder_path(self) -> Path:
        return self._scan_roots[0] if self._scan_roots else Path.cwd()

    def _set_scan_busy(self, busy: bool) -> None:
        self.is_scanning = busy
        if not self._scan:
            return
        self._scan.start_button.disabled = busy
        self._scan.pause_button.disabled = not busy
        self._scan.stop_button.disabled = not busy
        self._scan.browse_button.disabled = busy
        self._scan.add_drive_button.disabled = busy
        self._scan.clear_paths_button.disabled = busy
        self._request_page_update()

    def _clear_log(self, _event: ft.ControlEvent) -> None:
        if self._log:
            self._log.clear()
        self._last_status_message = ""
        self.page.update()

    def _request_stop(self, _event: ft.ControlEvent) -> None:
        if not self.is_scanning:
            return
        self._scan_id += 1
        self._is_paused = False
        self._log_msg("Stop requested — will halt after current file...", level="warning")

    def _toggle_pause(self, _event: ft.ControlEvent) -> None:
        if not self.is_scanning or not self._scan:
            return
        self._is_paused = not self._is_paused
        label = "Resume Scan" if self._is_paused else "Pause Scan"
        icon = ft.icons.PLAY_ARROW if self._is_paused else ft.icons.PAUSE
        self._scan.pause_button.text = label
        self._scan.pause_button.icon = icon
        self._log_msg("Scan paused." if self._is_paused else "Scan resumed.", level="status")
        self.page.update()

    def _wait_if_paused(self, scan_id: int) -> bool:
        """Chờ khi pause; trả True nếu cần dừng."""

        while self._is_paused and scan_id == self._scan_id:
            time.sleep(0.15)
        return scan_id != self._scan_id

    def _start_scan(self, _event: ft.ControlEvent) -> None:
        roots = self._get_valid_scan_roots()
        if roots is None:
            return
        self._scan_id += 1
        scan_id = self._scan_id
        self._is_paused = False
        self._set_scan_busy(True)
        threading.Thread(target=self._run_unified_scan, args=(roots, scan_id), daemon=True).start()

    def _refresh_results(self, _event: ft.ControlEvent) -> None:
        self.duplicate_rows = DuplicateGroupManager.prune_missing(self.duplicate_rows)
        self._refresh_result_table()
        self._log_msg("Results refreshed.", level="success")

    def _reset_scan_state(self) -> None:
        self.invalid_rows.clear()
        self.duplicate_rows.clear()
        self._all_scanned_files.clear()
        if self._progress:
            self._progress.progress_bar.value = 0
            self._progress.pct_label.value = "0%"
            self._progress.current_file_label.value = "Current file: —"
            self._progress.speed_label.value = "— files/s"
            self._progress.eta_label.value = "ETA: —"
            self._progress.elapsed_label.value = "Elapsed: 0:00"
        if self._results:
            self._results.selected_ids.clear()
            self._results.update_rows([])
        if self._preview:
            self._preview.show_file(None)
        self._update_stats()

    # ── Unified scan pipeline ─────────────────────────────

    def _run_unified_scan(self, roots: list[Path], scan_id: int) -> None:
        try:
            self.is_scanning = True
            self._scan_start_time = time.monotonic()
            self._ui(self._reset_scan_state)

            level = HashLevel(self.settings.hash_level)
            level_name = level.name.replace("_", " ")
            self._ui(self._log_msg, f"Hash level: {level_name}", level="info")

            if self.settings.auto_save:
                self._current_scan_db_id = self.db.insert_scan([str(r) for r in roots])

            def _should_stop() -> bool:
                return scan_id != self._scan_id or self._wait_if_paused(scan_id)

            roots_label = ", ".join(str(r) for r in roots[:3])
            if len(roots) > 3:
                roots_label += f" (+{len(roots) - 3} more)"
            self._ui(self._log_msg, f"Scanning: {roots_label}", level="status")

            files, sizes = self.inspector.scan_files_multi(roots)
            if _should_stop():
                return

            self._all_scanned_files = files
            total = max(len(files), 1)
            self._total_files = total
            self._ui(self._log_msg, f"Found {total} media files across {len(roots)} location(s).", level="info")

            # Stage 1: corruption check
            def _on_check_progress(index: int, t: int) -> None:
                if _should_stop():
                    return
                current = str(files[index - 1]) if index > 0 and index <= len(files) else ""
                self._ui(self._update_progress_ui, index, t * 2, current)

            self._ui(self._log_msg, "Checking for corrupted files...", level="status")
            results = self.inspector.check_files(
                files,
                progress_callback=_on_check_progress,
                should_stop=_should_stop,
            )
            if _should_stop():
                return

            invalid_rows = [invalid_result_to_row(r) for r in results if not r.is_valid]
            self.invalid_rows = invalid_rows
            for row in invalid_rows[:10]:
                sev = row.get("severity", "major").upper()
                self._ui(self._log_msg, f"Corrupted [{sev}]: {row['path']} | {row['error']}", level="warning")

            # Stage 2: duplicate detection
            def _on_dup_progress(completed: int, processed_total: int) -> None:
                if _should_stop():
                    return
                overall = total + completed
                overall_total = total + processed_total
                current = ""
                if completed > 0 and completed <= len(files):
                    current = str(files[min(completed - 1, len(files) - 1)])
                self._ui(self._update_progress_ui, overall, overall_total, current)

            self._ui(self._log_msg, "Detecting duplicates...", level="status")
            groups = self.duplicate_service.finder.find_duplicates(
                files,
                progress_callback=_on_dup_progress,
                should_stop=_should_stop,
                sizes=sizes,
                hash_level=level,
            )
            if _should_stop():
                return

            duplicate_rows = [duplicate_group_to_row(g) for g in groups]
            self.duplicate_rows = duplicate_rows

            self._ui(self._update_progress_ui, total * 2, total * 2, "")
            self._ui(self._refresh_result_table)

            dup_deletable = DuplicateGroupManager.count_deletable(duplicate_rows)
            self._ui(
                self._log_msg,
                f"Scan complete — {len(invalid_rows)} corrupted, {dup_deletable} duplicates, {total} files scanned.",
                level="success",
            )

            if self.settings.auto_save and self._current_scan_db_id is not None:
                recoverable = sum(
                    int(g.get("size", 0) or 0) * max(len(g.get("paths", [])) - 1, 0)
                    for g in duplicate_rows
                )
                self.db.finish_scan(
                    self._current_scan_db_id,
                    total_files=total,
                    duplicate_count=dup_deletable,
                    corrupted_count=len(invalid_rows),
                    recoverable_bytes=recoverable,
                )

        except (FileNotFoundError, NotADirectoryError, OSError) as exc:
            if scan_id == self._scan_id:
                self._ui(self._log_msg, f"Scan failed: {exc}", level="error")
        finally:
            cancelled = scan_id != self._scan_id
            if cancelled:
                self._ui(self._log_msg, "Scan stopped safely.", level="warning")
            if scan_id == self._scan_id or cancelled:
                self.is_scanning = False
                self._is_paused = False
                self._ui(self._set_scan_busy, False)
                if self._scan:
                    self._ui(lambda: setattr(self._scan.pause_button, "text", "Pause Scan"))
                    self._ui(lambda: setattr(self._scan.pause_button, "icon", ft.icons.PAUSE))

    # ── File actions ────────────────────────────────────

    def _open_path(self, path: Path) -> None:
        try:
            open_path(path)
            self._log_msg(f"Opened: {path.resolve()}")
        except OSError as exc:
            self._log_msg(f"Cannot open {path}: {exc}", level="error")

    def _confirm_delete_duplicates(self, _event: ft.ControlEvent) -> None:
        if not self.duplicate_rows:
            self._set_status("No duplicate groups to clean")
            return
        total_delete = DuplicateGroupManager.count_deletable(self.duplicate_rows)
        show_confirm_dialog(
            self.page,
            title="Confirm clean duplicates",
            content=f"Keep the first file in each group and delete {total_delete} duplicate copies.",
            confirm_label="Clean",
            on_confirm=self._delete_all_duplicates,
        )

    def _delete_all_duplicates(self, _event: ft.ControlEvent) -> None:
        close_dialog(self.page)
        paths_to_delete: list[Path] = []
        for group in list(self.duplicate_rows):
            paths = [Path(item) for item in group.get("paths", []) if isinstance(item, str)]
            paths_to_delete.extend(paths[1:])

        deleted_paths, failed = delete_paths(paths_to_delete)
        for path in deleted_paths:
            self._log_msg(f"Deleted duplicate: {path}", level="success")

        if deleted_paths:
            self.duplicate_rows = DuplicateGroupManager.remove_paths(self.duplicate_rows, set(deleted_paths))
            self.duplicate_rows = DuplicateGroupManager.prune_missing(self.duplicate_rows)
            self._refresh_result_table()

        self._set_status(f"Deleted {len(deleted_paths)} duplicate files")
        if failed:
            self._log_msg("Some duplicates could not be deleted: " + "; ".join(failed[:5]), level="error")

    def _delete_selected(self, _event: ft.ControlEvent) -> None:
        if not self._results or not self._results.selected_ids:
            self._set_status("No files selected")
            return
        selected_paths = [Path(r.path) for r in self._results.rows if r.row_id in self._results.selected_ids]
        deleted, failed = delete_paths(selected_paths)
        for path in deleted:
            self._log_msg(f"Deleted: {path}", level="success")
        if deleted:
            deleted_set = set(deleted)
            self.invalid_rows = [r for r in self.invalid_rows if Path(r["path"]).resolve() not in deleted_set]
            self.duplicate_rows = DuplicateGroupManager.remove_paths(self.duplicate_rows, deleted_set)
            self.duplicate_rows = DuplicateGroupManager.prune_missing(self.duplicate_rows)
            self._results.selected_ids.clear()
            self._refresh_result_table()
        if failed:
            self._log_msg("Some files could not be deleted: " + "; ".join(failed[:3]), level="error")

    def _delete_all_invalid_files(self, _event: ft.ControlEvent) -> None:
        if not self.invalid_rows:
            self._set_status("No corrupted files to clean")
            return
        sources = [Path(row["path"]) for row in list(self.invalid_rows)]
        deleted_paths, errors = delete_paths(sources)
        for path in deleted_paths:
            self._log_msg(f"Deleted corrupted: {path}", level="success")
        if deleted_paths:
            deleted_set = set(deleted_paths)
            self.invalid_rows = [r for r in self.invalid_rows if Path(r["path"]).resolve() not in deleted_set]
            self.duplicate_rows = DuplicateGroupManager.remove_paths(self.duplicate_rows, deleted_set)
            self._refresh_result_table()
        self._set_status(f"Deleted {len(deleted_paths)} corrupted files")
        if errors:
            self._log_msg("Some corrupted files could not be deleted: " + "; ".join(errors[:5]), level="error")

    def _quarantine_invalid_files(self, _event: ft.ControlEvent) -> None:
        if not self.invalid_rows:
            self._set_status("No corrupted files to quarantine")
            return
        destination = Path(QUARANTINE_DIR)
        destination.mkdir(parents=True, exist_ok=True)
        sources = [Path(row["path"]) for row in list(self.invalid_rows)]
        moved, errors = move_paths(sources, destination)
        if moved:
            self.invalid_rows = [r for r in self.invalid_rows if Path(r["path"]).exists()]
            self.duplicate_rows = DuplicateGroupManager.prune_missing(self.duplicate_rows)
            self._refresh_result_table()
        self._log_msg(f"Quarantined {moved} corrupted file(s) → {destination.resolve()}", level="success")
        if errors:
            self._log_msg("Quarantine errors: " + "; ".join(errors[:5]), level="error")

    def _export_all(self, _event: ft.ControlEvent) -> None:
        try:
            self.reporter.write_csv(Path(INVALID_MEDIA_CSV), self.invalid_rows)
            self.reporter.write_csv(Path(DUPLICATE_MEDIA_CSV), self.duplicate_rows)
            self._log_msg(f"Exported to {INVALID_MEDIA_CSV} and {DUPLICATE_MEDIA_CSV}", level="success")
        except OSError as exc:
            self._log_msg(f"Export failed: {exc}", level="error")

    def _save_report(self, _event: ft.ControlEvent) -> None:
        self._export_all(_event)

    def _delete_duplicate_path(self, duplicate_path: Path) -> None:
        try:
            force_delete_file(duplicate_path.resolve())
            self._log_msg(f"Deleted duplicate: {duplicate_path}", level="success")
            self.duplicate_rows = DuplicateGroupManager.remove_path(self.duplicate_rows, duplicate_path.resolve())
            self.duplicate_rows = DuplicateGroupManager.prune_missing(self.duplicate_rows)
            self._refresh_result_table()
        except Exception as exc:  # noqa: BLE001
            self._log_msg(describe_delete_error(duplicate_path, exc), level="error")


# Backward-compatible alias
MediaToolApp = MediaScannerProApp


def launch() -> None:
    """Khởi chạy ứng dụng Flet."""

    def _app(page: ft.Page) -> None:
        MediaScannerProApp(page).build()

    ft.app(target=_app)
