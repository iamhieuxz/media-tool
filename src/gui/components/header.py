"""Header — logo M, search, settings, theme, profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.constants import APP_TITLE
from src.gui.theme import AppTheme, glass_panel, logo_badge


@dataclass
class HeaderControls:
    container: ft.Container
    search_field: ft.TextField
    theme_toggle: ft.IconButton
    settings_button: ft.IconButton


def build_header(
    *,
    on_search_change: Callable[[ft.ControlEvent], None] | None = None,
    on_settings: Callable[[ft.ControlEvent], None] | None = None,
    on_theme_toggle: Callable[[ft.ControlEvent], None] | None = None,
) -> HeaderControls:
    search_field = ft.TextField(
        hint_text="Search media...",
        prefix_icon=ft.icons.SEARCH,
        expand=True,
        height=42,
        border_radius=AppTheme.RADIUS_MD,
        bgcolor=AppTheme.SURFACE_ELEVATED,
        border_color=AppTheme.BORDER,
        focused_border_color=AppTheme.ACCENT,
        text_style=ft.TextStyle(color=AppTheme.TEXT_PRIMARY, size=AppTheme.FONT_BODY),
        content_padding=ft.padding.symmetric(horizontal=12, vertical=0),
        on_change=on_search_change,
    )

    def _icon_btn(icon: str, tooltip: str, on_click) -> ft.IconButton:
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            icon_color=AppTheme.TEXT_SECONDARY,
            icon_size=20,
            on_click=on_click,
            style=ft.ButtonStyle(
                bgcolor=AppTheme.SURFACE_ELEVATED,
                shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
                padding=8,
            ),
        )

    theme_toggle = _icon_btn(ft.icons.DARK_MODE, "Dark / Light mode", on_theme_toggle)
    settings_button = _icon_btn(ft.icons.SETTINGS, "Settings", on_settings)

    profile = ft.Container(
        width=36,
        height=36,
        border_radius=18,
        bgcolor=AppTheme.ACCENT_SOFT,
        border=ft.border.all(1, AppTheme.ACCENT),
        alignment=ft.alignment.center,
        content=ft.Text("JS", size=11, weight=ft.FontWeight.BOLD, color=AppTheme.ACCENT_HOVER),
    )

    container = glass_panel(
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=12,
                    controls=[
                        logo_badge(),
                        ft.Text(
                            APP_TITLE,
                            size=AppTheme.FONT_TITLE,
                            weight=ft.FontWeight.BOLD,
                            color=AppTheme.TEXT_PRIMARY,
                        ),
                    ],
                ),
                ft.Container(width=420, content=search_field),
                ft.Row(spacing=6, controls=[settings_button, theme_toggle, profile]),
            ],
        ),
        padding=12,
    )

    return HeaderControls(
        container=container,
        search_field=search_field,
        theme_toggle=theme_toggle,
        settings_button=settings_button,
    )
