"""Footer — Export / Clean actions (mockup bottom bar)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, danger_button, ghost_button, primary_button


@dataclass
class FooterControls:
    container: ft.Container
    export_button: ft.TextButton
    save_report_button: ft.TextButton
    delete_selected_button: ft.TextButton
    clean_duplicates_button: ft.ElevatedButton
    clean_corrupted_button: ft.Control


def build_footer(
    *,
    on_export: Callable[[ft.ControlEvent], None],
    on_save_report: Callable[[ft.ControlEvent], None],
    on_delete_selected: Callable[[ft.ControlEvent], None],
    on_clean_duplicates: Callable[[ft.ControlEvent], None],
    on_clean_corrupted: Callable[[ft.ControlEvent], None],
) -> FooterControls:
    export_button = ghost_button("Export Results", ft.icons.UPLOAD_FILE, on_export)
    save_report_button = ghost_button("Save Report", ft.icons.SAVE_ALT, on_save_report)
    delete_selected_button = ghost_button("Delete All Selected", ft.icons.DELETE_OUTLINE, on_delete_selected)
    clean_duplicates_button = primary_button("Clean Duplicates", ft.icons.AUTO_FIX_HIGH, on_clean_duplicates)
    clean_corrupted_button = danger_button("Clean Corrupted Files", ft.icons.DELETE_FOREVER, on_clean_corrupted, filled=True)

    container = ft.Container(
        padding=ft.padding.symmetric(vertical=8, horizontal=4),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(spacing=4, controls=[export_button, save_report_button, delete_selected_button]),
                ft.Row(spacing=10, controls=[clean_duplicates_button, clean_corrupted_button]),
            ],
        ),
    )

    return FooterControls(
        container=container,
        export_button=export_button,
        save_report_button=save_report_button,
        delete_selected_button=delete_selected_button,
        clean_duplicates_button=clean_duplicates_button,
        clean_corrupted_button=clean_corrupted_button,
    )
