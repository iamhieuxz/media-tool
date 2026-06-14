"""Log panel — Bottom Activity Log (cột phải)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, glass_panel

LogLevel = Literal["info", "warning", "error", "success", "status"]

_LEVEL_COLORS: dict[LogLevel, str] = {
    "info": AppTheme.INFO,
    "status": AppTheme.INFO,
    "warning": AppTheme.WARNING,
    "error": AppTheme.DANGER,
    "success": AppTheme.SUCCESS,
}

_LEVEL_LABELS: dict[LogLevel, str] = {
    "info": "Information",
    "status": "Information",
    "warning": "Warning",
    "error": "Error",
    "success": "Success",
}


@dataclass
class LogPanelControls:
    container: ft.Container
    log_list: ft.Column
    log_body: ft.Container
    _expanded: bool = True

    def append(self, message: str, level: LogLevel = "info") -> None:
        text_color = _LEVEL_COLORS.get(level, AppTheme.INFO)
        label = _LEVEL_LABELS.get(level, "Information")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_list.controls.append(
            ft.Text(
                f"[{ts}] {label} | {message}",
                size=AppTheme.FONT_CAPTION,
                color=text_color,
                selectable=True,
            )
        )

    def clear(self) -> None:
        self.log_list.controls.clear()

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self.log_body.visible = self._expanded


def build_log_panel(*, on_clear: Callable, max_entries: int = 500) -> LogPanelControls:
    log_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
    log_body = ft.Container(
        expand=True,
        padding=10,
        border_radius=AppTheme.RADIUS_MD,
        bgcolor=AppTheme.BG,
        border=ft.border.all(1, AppTheme.BORDER),
        content=log_list,
    )

    controls = LogPanelControls(
        container=ft.Container(),
        log_list=log_list,
        log_body=log_body,
    )

    def _toggle(_e: ft.ControlEvent) -> None:
        controls.toggle()
        chevron.icon = ft.icons.EXPAND_LESS if controls._expanded else ft.icons.EXPAND_MORE
        log_body.update()

    chevron = ft.IconButton(
        icon=ft.icons.EXPAND_LESS,
        icon_size=18,
        icon_color=AppTheme.TEXT_MUTED,
        on_click=_toggle,
        tooltip="Thu gọn / Mở rộng",
    )

    header_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Text(
                "Bottom Activity Log",
                size=AppTheme.FONT_BODY,
                weight=ft.FontWeight.W_600,
                color=AppTheme.TEXT_PRIMARY,
            ),
            ft.Row(
                spacing=0,
                controls=[
                    ft.IconButton(
                        icon=ft.icons.CLEAR_ALL,
                        icon_size=18,
                        icon_color=AppTheme.TEXT_MUTED,
                        tooltip="Clear log",
                        on_click=on_clear,
                    ),
                    chevron,
                ],
            ),
        ],
    )

    container = glass_panel(
        ft.Column(
            expand=True,
            spacing=8,
            controls=[header_row, log_body],
        ),
        expand=True,
        padding=12,
    )
    controls.container = container

    original_append = controls.append

    def _append_with_limit(message: str, level: LogLevel = "info") -> None:
        original_append(message, level)
        if len(log_list.controls) > max_entries:
            log_list.controls = log_list.controls[-max_entries:]

    controls.append = _append_with_limit  # type: ignore[method-assign]
    return controls
