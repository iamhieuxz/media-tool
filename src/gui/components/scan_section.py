"""Scan section — path, Browse, Start/Pause/Stop/Refresh."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, accent_outline_button, glass_panel, primary_button, secondary_button


@dataclass
class ScanSectionControls:
    container: ft.Container
    path_field: ft.TextField
    path_chips: ft.Row
    browse_button: ft.ElevatedButton
    add_drive_button: ft.IconButton
    clear_paths_button: ft.IconButton
    start_button: ft.ElevatedButton
    pause_button: ft.OutlinedButton
    stop_button: ft.Control
    refresh_button: ft.OutlinedButton


def build_scan_section(
    *,
    on_browse: Callable[[ft.ControlEvent], None],
    on_add_drive: Callable[[ft.ControlEvent], None],
    on_clear_paths: Callable[[ft.ControlEvent], None],
    on_start: Callable[[ft.ControlEvent], None],
    on_pause: Callable[[ft.ControlEvent], None],
    on_stop: Callable[[ft.ControlEvent], None],
    on_refresh: Callable[[ft.ControlEvent], None],
) -> ScanSectionControls:
    path_field = ft.TextField(
        hint_text="Select folder or drive to scan...",
        prefix_icon=ft.icons.FOLDER_OUTLINED,
        expand=True,
        height=44,
        border_radius=AppTheme.RADIUS_MD,
        border_color=AppTheme.BORDER,
        focused_border_color=AppTheme.ACCENT,
        bgcolor=AppTheme.SURFACE_ELEVATED,
        text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=AppTheme.FONT_BODY),
        content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
    )

    path_chips = ft.Row(wrap=True, spacing=6, run_spacing=4, visible=False)

    browse_button = accent_outline_button("Browse...", ft.icons.FOLDER_OPEN, on_browse)
    add_drive_button = ft.IconButton(
        icon=ft.icons.STORAGE,
        tooltip="Add drive",
        icon_color=AppTheme.TEXT_MUTED,
        on_click=on_add_drive,
    )
    clear_paths_button = ft.IconButton(
        icon=ft.icons.CLOSE,
        tooltip="Clear paths",
        icon_color=AppTheme.TEXT_MUTED,
        on_click=on_clear_paths,
    )

    start_button = primary_button("Start Scan", ft.icons.PLAY_ARROW_ROUNDED, on_start)
    pause_button = secondary_button("Pause Scan", ft.icons.PAUSE_ROUNDED, on_pause)
    pause_button.disabled = True
    stop_button = secondary_button("Stop Scan", ft.icons.STOP_ROUNDED, on_stop)
    stop_button.disabled = True
    refresh_button = secondary_button("Refresh Results", ft.icons.REFRESH, on_refresh)

    container = glass_panel(
        ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(expand=True, content=path_field),
                        browse_button,
                        add_drive_button,
                        clear_paths_button,
                    ],
                ),
                path_chips,
                ft.Row(
                    spacing=10,
                    controls=[start_button, pause_button, stop_button, refresh_button],
                ),
            ],
        ),
    )

    return ScanSectionControls(
        container=container,
        path_field=path_field,
        path_chips=path_chips,
        browse_button=browse_button,
        add_drive_button=add_drive_button,
        clear_paths_button=clear_paths_button,
        start_button=start_button,
        pause_button=pause_button,
        stop_button=stop_button,
        refresh_button=refresh_button,
    )
