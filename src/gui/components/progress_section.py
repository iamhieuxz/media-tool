"""Progress section — thanh tiến trình kiểu mockup."""

from __future__ import annotations

from dataclasses import dataclass

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, glass_panel


@dataclass
class ProgressControls:
    container: ft.Container
    progress_bar: ft.ProgressBar
    pct_label: ft.Text
    current_file_label: ft.Text
    speed_label: ft.Text
    eta_label: ft.Text
    elapsed_label: ft.Text


def build_progress_section() -> ProgressControls:
    progress_bar = ft.ProgressBar(value=0, expand=True)
    progress_bar.color = AppTheme.ACCENT
    progress_bar.bgcolor = AppTheme.SURFACE_ELEVATED
    progress_bar.bar_height = 10
    progress_bar.border_radius = 6

    pct_label = ft.Text(
        "Scan percentage (0%)",
        color=AppTheme.INFO,
        size=AppTheme.FONT_CAPTION,
        weight=ft.FontWeight.W_600,
    )
    eta_label = ft.Text(
        "Estimated remaining: —",
        size=AppTheme.FONT_CAPTION,
        color=AppTheme.TEXT_SECONDARY,
    )
    current_file_label = ft.Text(
        "Current file: —",
        size=AppTheme.FONT_CAPTION,
        color=AppTheme.TEXT_MUTED,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    speed_label = ft.Text(visible=False)
    elapsed_label = ft.Text(visible=False)

    container = glass_panel(
        ft.Column(
            spacing=8,
            controls=[
                progress_bar,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[pct_label, eta_label],
                ),
                current_file_label,
            ],
        ),
        padding=14,
    )

    return ProgressControls(
        container=container,
        progress_bar=progress_bar,
        pct_label=pct_label,
        current_file_label=current_file_label,
        speed_label=speed_label,
        eta_label=eta_label,
        elapsed_label=elapsed_label,
    )
