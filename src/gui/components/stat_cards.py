"""Statistic cards — 4 thẻ theo mockup."""

from __future__ import annotations

from dataclasses import dataclass

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, stat_card


@dataclass
class StatCardControls:
    row: ft.Row
    total_value: ft.Text
    duplicate_value: ft.Text
    corrupted_value: ft.Text
    recoverable_value: ft.Text
    speed_value: ft.Text


def _value_text(initial: str = "0") -> ft.Text:
    return ft.Text(initial, size=18, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT_PRIMARY)


def build_stat_cards() -> StatCardControls:
    total_value = _value_text("0")
    duplicate_value = _value_text("0")
    corrupted_value = _value_text("0")
    recoverable_value = _value_text("0 B")
    speed_value = _value_text("—")

    row = ft.Row(
        spacing=10,
        controls=[
            stat_card("Total files scanned", total_value, AppTheme.ACCENT, ft.icons.INSERT_DRIVE_FILE_OUTLINED),
            stat_card("Duplicate files found", duplicate_value, AppTheme.DUPLICATE, ft.icons.COPY_ALL),
            stat_card("Corrupted files found", corrupted_value, AppTheme.DANGER, ft.icons.BROKEN_IMAGE_OUTLINED),
            stat_card("Storage space recoverable", recoverable_value, AppTheme.INFO, ft.icons.SD_STORAGE_OUTLINED),
        ],
    )

    return StatCardControls(
        row=row,
        total_value=total_value,
        duplicate_value=duplicate_value,
        corrupted_value=corrupted_value,
        recoverable_value=recoverable_value,
        speed_value=speed_value,
    )
