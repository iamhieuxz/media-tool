"""Result tabs + table — thumbnails, sort, filter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, ghost_button, glass_panel, secondary_button
from src.utils.media_metadata import extract_metadata
from src.utils.thumbnail_cache import ThumbnailCache

TabName = Literal["duplicates", "corrupted", "all"]
MAX_DISPLAY_ROWS = 500
FILENAME_MAX_CHARS = 34
SortColumn = Literal["filename", "file_type", "resolution", "size", "group_id", "similarity", "date_modified", "severity"]


@dataclass
class ResultRow:
    """Một dòng trong bảng kết quả."""

    row_id: str
    path: str
    filename: str
    file_type: str
    resolution: str
    size: int
    group_id: str
    similarity: str
    date_modified: str
    category: TabName
    severity: str = "—"
    selected: bool = False


@dataclass
class ResultTabsControls:
    """Controls trả về từ build_result_tabs."""

    container: ft.Container
    table: ft.DataTable
    tab_bar: ft.Tabs
    rows: list[ResultRow] = field(default_factory=list)
    selected_ids: set[str] = field(default_factory=set)
    _active_tab: TabName = "duplicates"
    _search_query: str = ""
    _sort_column: SortColumn = "filename"
    _sort_asc: bool = True
    _on_row_select: Callable[[ResultRow], None] | None = None
    _on_preview_selected: Callable[[], None] | None = None
    _table_container: ft.Container | None = None
    _thumb_cache: ThumbnailCache = field(default_factory=ThumbnailCache)
    _status_label: ft.Text | None = None
    _delete_selected_btn: ft.TextButton | None = None
    _select_all_checkbox: ft.Checkbox | None = None

    def set_delete_button(self, button: ft.TextButton) -> None:
        self._delete_selected_btn = button

    def update_selection_count(self, selected: int, duplicate_total: int) -> None:
        if self._delete_selected_btn:
            self._delete_selected_btn.text = f"Delete Selected Duplicates ({selected:,} selected)"
            if self._delete_selected_btn.page:
                self._delete_selected_btn.update()

    def set_thumbnail_cache(self, cache: ThumbnailCache) -> None:
        self._thumb_cache = cache

    def set_on_row_select(self, callback: Callable[[ResultRow], None]) -> None:
        self._on_row_select = callback

    def set_on_preview_selected(self, callback: Callable[[], None]) -> None:
        self._on_preview_selected = callback

    def set_search_query(self, query: str) -> None:
        self._search_query = query.strip().lower()
        self._rebuild_table()

    def set_active_tab(self, tab: TabName) -> None:
        self._active_tab = tab
        self._rebuild_table()

    def update_rows(self, rows: list[ResultRow]) -> None:
        self.rows = rows
        self._rebuild_table()

    def get_selected_rows(self) -> list[ResultRow]:
        return [r for r in self.rows if r.row_id in self.selected_ids]

    def get_filtered_rows(self) -> list[ResultRow]:
        filtered = [r for r in self.rows if self._matches_tab(r)]
        if self._search_query:
            q = self._search_query
            filtered = [
                r
                for r in filtered
                if q in r.filename.lower()
                or q in r.path.lower()
                or q in r.file_type.lower()
                or q in r.group_id.lower()
                or q in r.resolution.lower()
                or q in r.severity.lower()
            ]
        filtered = self._sort_rows(filtered)
        return filtered[:MAX_DISPLAY_ROWS]

    def _sort_rows(self, rows: list[ResultRow]) -> list[ResultRow]:
        col = self._sort_column

        def key_fn(row: ResultRow):
            if col == "size":
                return row.size
            if col == "similarity":
                text = row.similarity.rstrip("%")
                try:
                    return float(text)
                except ValueError:
                    return 0.0
            return str(getattr(row, col, "")).lower()

        return sorted(rows, key=key_fn, reverse=not self._sort_asc)

    def _on_sort(self, column: SortColumn) -> Callable[[ft.DataColumnSortEvent], None]:
        def handler(event: ft.DataColumnSortEvent) -> None:
            self._sort_column = column
            self._sort_asc = event.ascending
            self._rebuild_table()
            if self._table_container and self._table_container.page:
                self._table_container.update()

        return handler

    def _matches_tab(self, row: ResultRow) -> bool:
        if self._active_tab == "all":
            return True
        if self._active_tab == "duplicates":
            return row.category == "duplicates"
        return row.category == "corrupted"

    def _toggle_select(self, row_id: str, selected: bool) -> None:
        if selected:
            self.selected_ids.add(row_id)
        else:
            self.selected_ids.discard(row_id)
        for row in self.rows:
            if row.row_id == row_id:
                row.selected = selected
                if selected and self._on_row_select:
                    self._on_row_select(row)
                break
        self._sync_select_all_checkbox()
        if self._delete_selected_btn:
            dup_selected = sum(1 for r in self.rows if r.row_id in self.selected_ids and r.category == "duplicates")
            self.update_selection_count(dup_selected, dup_selected)

    def _sync_select_all_checkbox(self) -> None:
        if not self._select_all_checkbox:
            return
        filtered = self.get_filtered_rows()
        if not filtered:
            self._select_all_checkbox.value = False
            self._select_all_checkbox.disabled = True
        else:
            self._select_all_checkbox.disabled = False
            self._select_all_checkbox.value = all(r.row_id in self.selected_ids for r in filtered)
        if self._select_all_checkbox.page:
            self._select_all_checkbox.update()

    def _toggle_select_all(self, selected: bool) -> None:
        filtered = self.get_filtered_rows()
        for row in filtered:
            if selected:
                self.selected_ids.add(row.row_id)
            else:
                self.selected_ids.discard(row.row_id)
            row.selected = selected
        if self._delete_selected_btn:
            dup_selected = sum(1 for r in self.rows if r.row_id in self.selected_ids and r.category == "duplicates")
            self.update_selection_count(dup_selected, dup_selected)
        self._rebuild_table()

    def _thumb_cell(self, path: Path) -> ft.Control:
        thumb = self._thumb_cache.get_thumbnail(path)
        if thumb is not None:
            return ft.Image(src=str(thumb), width=40, height=40, fit=ft.ImageFit.COVER, border_radius=4)
        return ft.Container(
            width=40,
            height=40,
            border_radius=4,
            bgcolor=AppTheme.SURFACE_ELEVATED,
            alignment=ft.alignment.center,
            content=ft.Icon(ft.icons.INSERT_PHOTO, size=16, color=AppTheme.TEXT_MUTED),
        )

    def _filename_cell(self, row: ResultRow) -> ft.Control:
        full_name = row.filename
        if len(full_name) > FILENAME_MAX_CHARS:
            display_name = full_name[: FILENAME_MAX_CHARS - 1] + "…"
            return ft.Tooltip(
                message=full_name,
                content=ft.Text(display_name, size=11, max_lines=1, overflow=ft.TextOverflow.CLIP),
            )
        return ft.Text(full_name, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)

    def _rebuild_table(self) -> None:
        filtered = self.get_filtered_rows()
        total_matching = len([r for r in self.rows if self._matches_tab(r)])
        if self._status_label:
            shown = len(filtered)
            suffix = f" (showing {shown} of {total_matching})" if total_matching > shown else ""
            self._status_label.value = f"{total_matching} rows{suffix}"

        self._sync_select_all_checkbox()

        data_rows: list[ft.DataRow] = []
        for row in filtered:
            path = Path(row.path)
            checkbox = ft.Checkbox(
                value=row.row_id in self.selected_ids,
                on_change=lambda e, rid=row.row_id: self._toggle_select(rid, bool(e.control.value)),
            )

            data_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(checkbox),
                        ft.DataCell(self._thumb_cell(path)),
                        ft.DataCell(self._filename_cell(row)),
                        ft.DataCell(ft.Text(row.file_type, size=11)),
                        ft.DataCell(ft.Text(row.resolution, size=11)),
                        ft.DataCell(ft.Text(_format_size(row.size), size=11)),
                        ft.DataCell(ft.Text(row.group_id, size=11)),
                        ft.DataCell(ft.Text(row.date_modified, size=11)),
                    ],
                    on_select_changed=lambda _e, r=row: self._on_row_click(r),
                )
            )
        self.table.rows = data_rows
        if self._table_container and self._table_container.page:
            self._table_container.update()

    def _on_row_click(self, row: ResultRow) -> None:
        if self._on_row_select:
            self._on_row_select(row)


def _format_size(size: int) -> str:
    if size >= 1_073_741_824:
        return f"{size / 1_073_741_824:.1f} GB"
    if size >= 1_048_576:
        return f"{size / 1_048_576:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _file_date(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    except OSError:
        return "—"


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _resolution_for(path: Path, fallback: str = "") -> str:
    if fallback:
        return fallback
    try:
        return extract_metadata(path).resolution
    except OSError:
        return "—"


def rows_from_duplicates(duplicate_rows: list[dict[str, object]]) -> list[ResultRow]:
    result: list[ResultRow] = []
    for g_idx, group in enumerate(duplicate_rows, start=1):
        group_id = f"{g_idx:04d}"
        size = int(group.get("size", 0) or 0)
        paths = [p for p in group.get("paths", []) if isinstance(p, str)]
        match_type = str(group.get("match_type", "exact"))
        path_sims = group.get("path_similarities", {})
        if not isinstance(path_sims, dict):
            path_sims = {}
        group_sim = group.get("similarity", 100.0)
        for p_idx, path_str in enumerate(paths):
            path = Path(path_str)
            if path_str in path_sims:
                sim_text = f"{path_sims[path_str]}%"
            elif match_type == "perceptual":
                sim_text = f"{group_sim}%"
            else:
                sim_text = "100%"
            result.append(
                ResultRow(
                    row_id=f"dup-{group_id}-{p_idx}",
                    path=path_str,
                    filename=path.name,
                    file_type=path.suffix.lstrip(".").upper() or "—",
                    resolution=_resolution_for(path),
                    size=size if size else _safe_size(path),
                    group_id=group_id,
                    similarity=sim_text,
                    date_modified=_file_date(path),
                    category="duplicates",
                    severity="—",
                )
            )
    return result


def rows_from_invalid(invalid_rows: list[dict[str, str]]) -> list[ResultRow]:
    result: list[ResultRow] = []
    for idx, row in enumerate(invalid_rows):
        path = Path(row["path"])
        result.append(
            ResultRow(
                row_id=f"err-{idx}",
                path=row["path"],
                filename=path.name,
                file_type=row.get("media_type", "—"),
                resolution=row.get("resolution") or _resolution_for(path),
                size=_safe_size(path),
                group_id="—",
                similarity="—",
                date_modified=_file_date(path),
                category="corrupted",
                severity=row.get("severity", "major"),
            )
        )
    return result


def build_result_tabs(
    *,
    on_tab_change: Callable[[TabName], None] | None = None,
    on_preview: Callable[[], None] | None = None,
    on_show_duplicates: Callable[[], None] | None = None,
    on_delete_selected: Callable[[], None] | None = None,
    on_recycle_bin: Callable[[], None] | None = None,
) -> ResultTabsControls:
    status_label = ft.Text("", size=AppTheme.FONT_CAPTION, color=AppTheme.TEXT_MUTED)
    holder: list[ResultTabsControls] = []

    def _on_sort(column: SortColumn) -> Callable[[ft.DataColumnSortEvent], None]:
        def handler(event: ft.DataColumnSortEvent) -> None:
            ctrl = holder[0]
            ctrl._sort_column = column
            ctrl._sort_asc = event.ascending
            ctrl._rebuild_table()

        return handler

    def _col(label: str, column: SortColumn) -> ft.DataColumn:
        return ft.DataColumn(
            ft.Text(label, size=11, weight=ft.FontWeight.W_600),
            on_sort=_on_sort(column),
        )

    select_all_checkbox = ft.Checkbox(
        value=False,
        disabled=True,
        on_change=lambda e: holder[0]._toggle_select_all(bool(e.control.value)) if holder else None,
    )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Container(content=select_all_checkbox, alignment=ft.alignment.center_left, width=32)),
            ft.DataColumn(ft.Text("", size=10)),
            _col("Filename", "filename"),
            _col("Type", "file_type"),
            _col("Resolution", "resolution"),
            _col("Size", "size"),
            _col("Group ID", "group_id"),
            _col("Date modified", "date_modified"),
        ],
        rows=[],
        heading_row_color=AppTheme.SURFACE_ELEVATED,
        heading_row_height=40,
        data_row_min_height=48,
        border=ft.border.all(1, AppTheme.BORDER),
        border_radius=AppTheme.RADIUS_MD,
        column_spacing=10,
        horizontal_lines=ft.BorderSide(1, AppTheme.BORDER),
        sort_column_index=2,
        sort_ascending=True,
    )

    table_container = ft.Container(
        expand=True,
        content=ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[table]),
    )

    def _on_tabs_change(e: ft.ControlEvent) -> None:
        idx = e.control.selected_index
        tab_map: list[TabName] = ["duplicates", "corrupted"]
        if 0 <= idx < len(tab_map):
            holder[0].set_active_tab(tab_map[idx])
            if on_tab_change:
                on_tab_change(tab_map[idx])

    tab_bar = ft.Tabs(
        selected_index=0,
        animation_duration=150,
        divider_color=AppTheme.BORDER,
        indicator_color=AppTheme.ACCENT,
        label_color=AppTheme.TEXT_MUTED,
        unselected_label_color=AppTheme.TEXT_MUTED,
        on_change=_on_tabs_change,
        tabs=[
            ft.Tab(text="Duplicate Files"),
            ft.Tab(text="Corrupted Files"),
        ],
    )

    delete_selected_btn = ghost_button(
        "Delete Selected Duplicates (0 selected)",
        ft.icons.DELETE_OUTLINE,
        on_delete_selected or (lambda _e: None),
    )

    def _on_show_dup(_e: ft.ControlEvent) -> None:
        if holder:
            holder[0].set_active_tab("duplicates")
        if on_show_duplicates:
            on_show_duplicates()

    action_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Row(
                spacing=4,
                wrap=True,
                controls=[
                    ghost_button("Show Duplicates", ft.icons.FILTER_LIST, _on_show_dup),
                    ghost_button("Preview Selected", ft.icons.PREVIEW_OUTLINED, on_preview or (lambda _e: None)),
                    delete_selected_btn,
                    ghost_button("Move to Recycle Bin", ft.icons.DELETE_SWEEP_OUTLINED, on_recycle_bin or (lambda _e: None)),
                ],
            ),
            status_label,
        ],
    )

    container = glass_panel(
        ft.Column(
            expand=True,
            spacing=10,
            controls=[tab_bar, action_row, table_container],
        ),
        expand=True,
    )

    controls_ref = ResultTabsControls(
        container=container,
        table=table,
        tab_bar=tab_bar,
        _table_container=table_container,
        _status_label=status_label,
        _select_all_checkbox=select_all_checkbox,
    )
    holder.append(controls_ref)
    controls_ref.set_delete_button(delete_selected_btn)
    return controls_ref
