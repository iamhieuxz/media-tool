"""Settings dialog — hash level, workers, theme (foundation)."""

from __future__ import annotations

from collections.abc import Callable

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.core.hash_engine import HashLevel
from src.db.models import AppSettings
from src.gui.theme import AppTheme, primary_button, secondary_button


def show_settings_dialog(
    page: ft.Page,
    settings: AppSettings,
    on_save: Callable[[AppSettings], None],
) -> None:
    """Hiển thị dialog cài đặt cơ bản."""

    hash_dropdown = ft.Dropdown(
        label="Hash Level",
        value=str(settings.hash_level),
        options=[
            ft.dropdown.Option(str(int(HashLevel.EXACT_MD5)), "Level 1 — MD5 (legacy)"),
            ft.dropdown.Option(str(int(HashLevel.EXACT_SHA256)), "Level 1 — SHA256"),
            ft.dropdown.Option(str(int(HashLevel.PERCEPTUAL)), "Level 2 — Perceptual (pHash / dHash)"),
        ],
        border_color=AppTheme.BORDER,
        focused_border_color=AppTheme.ACCENT,
    )
    threshold_field = ft.TextField(
        label="Similarity Threshold (%)",
        value=str(settings.similarity_threshold),
        border_color=AppTheme.BORDER,
    )
    workers_field = ft.TextField(
        label="Worker Count (0 = auto)",
        value=str(settings.worker_count),
        border_color=AppTheme.BORDER,
    )
    auto_save_switch = ft.Switch(label="Auto Save Results", value=settings.auto_save)

    def _save(_event: ft.ControlEvent) -> None:
        try:
            updated = AppSettings(
                hash_level=int(hash_dropdown.value or settings.hash_level),
                similarity_threshold=float(threshold_field.value or settings.similarity_threshold),
                worker_count=int(workers_field.value or 0),
                theme=settings.theme,
                language=settings.language,
                auto_save=auto_save_switch.value or False,
            )
        except ValueError:
            return
        on_save(updated)
        if page.dialog:
            page.dialog.open = False
            page.update()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=AppTheme.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_LG),
        title=ft.Text("Settings", color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600),
        content=ft.Column(
            tight=True,
            spacing=12,
            width=400,
            controls=[hash_dropdown, threshold_field, workers_field, auto_save_switch],
        ),
        actions=[
            secondary_button("Cancel", ft.icons.CLOSE, lambda _e: _close(page)),
            primary_button("Save", ft.icons.SAVE, _save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.dialog = dialog
    dialog.open = True
    page.update()


def _close(page: ft.Page) -> None:
    if page.dialog:
        page.dialog.open = False
        page.update()
