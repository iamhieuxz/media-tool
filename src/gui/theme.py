"""Bảng màu và style — Media Scanner Pro (mockup dark / glass)."""

from __future__ import annotations

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.constants import APP_TITLE


class AppTheme:
    """Token màu sắc theo mockup."""

    BG = "#0a0e17"
    SURFACE = "#111827"
    SURFACE_ELEVATED = "#1a2332"
    SURFACE_CARD = "#1e293b"
    SURFACE_GLASS = "#151d2bcc"
    BORDER = "#2a3548"
    BORDER_LIGHT = "#334155"

    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#94a3b8"
    TEXT_MUTED = "#64748b"

    ACCENT = "#3b82f6"
    ACCENT_HOVER = "#60a5fa"
    ACCENT_SOFT = "#1e3a5f"
    ACCENT_GRADIENT_START = "#2563eb"
    ACCENT_GRADIENT_END = "#3b82f6"

    SUCCESS = "#22c55e"
    SUCCESS_SOFT = "#14532d"
    WARNING = "#f59e0b"
    WARNING_SOFT = "#78350f"
    DANGER = "#ef4444"
    DANGER_SOFT = "#7f1d1d"
    INFO = "#38bdf8"
    INFO_SOFT = "#0c4a6e"

    DUPLICATE = "#f59e0b"
    DUPLICATE_SOFT = "#78350f"

    RADIUS_SM = 8
    RADIUS_MD = 10
    RADIUS_LG = 12
    RADIUS_XL = 14

    FONT_TITLE = 22
    FONT_HEADING = 15
    FONT_BODY = 13
    FONT_CAPTION = 11


def apply_page_theme(page: ft.Page) -> None:
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = AppTheme.BG
    page.padding = 12
    page.spacing = 0
    page.window_min_width = 1100
    page.window_min_height = 720
    page.window_width = 1360
    page.window_height = 900
    page.theme = ft.Theme(color_scheme_seed=AppTheme.ACCENT, font_family="Segoe UI")


def glass_panel(content: ft.Control, *, expand: bool = False, padding: int = 14) -> ft.Container:
    """Panel kiểu glassmorphism — viền mảnh, nền trong suốt."""

    return ft.Container(
        expand=expand,
        padding=padding,
        border_radius=AppTheme.RADIUS_LG,
        bgcolor=AppTheme.SURFACE,
        border=ft.border.all(1, AppTheme.BORDER),
        content=content,
    )


def panel_container(content: ft.Control, *, expand: bool = False) -> ft.Container:
    return glass_panel(content, expand=expand)


def logo_badge() -> ft.Container:
    """Logo chữ M theo mockup."""

    return ft.Container(
        width=42,
        height=42,
        border_radius=AppTheme.RADIUS_MD,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[AppTheme.ACCENT_GRADIENT_START, AppTheme.ACCENT_GRADIENT_END],
        ),
        alignment=ft.alignment.center,
        content=ft.Text("M", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
    )


def primary_button(label: str, icon: str, on_click, color: str = AppTheme.ACCENT) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label,
        icon=icon,
        on_click=on_click,
        bgcolor=color,
        color="#ffffff",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
            elevation=0,
            overlay_color=ft.colors.with_opacity(0.08, "#ffffff"),
        ),
    )


def accent_outline_button(label: str, icon: str, on_click) -> ft.ElevatedButton:
    """Nút Browse... màu xanh mockup."""

    return ft.ElevatedButton(
        label,
        icon=icon,
        on_click=on_click,
        bgcolor=AppTheme.ACCENT,
        color="#ffffff",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            elevation=0,
        ),
    )


def secondary_button(label: str, icon: str, on_click) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=AppTheme.TEXT_SECONDARY,
            bgcolor=AppTheme.SURFACE_ELEVATED,
            shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            side=ft.BorderSide(1, AppTheme.BORDER),
        ),
    )


def ghost_button(label: str, icon: str, on_click) -> ft.TextButton:
    """Nút toolbar phụ — phẳng."""

    return ft.TextButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=AppTheme.TEXT_SECONDARY,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_SM),
        ),
    )


def danger_button(label: str, icon: str, on_click, *, filled: bool = False) -> ft.Control:
    style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        elevation=0,
    )
    if filled:
        return ft.ElevatedButton(
            label,
            icon=icon,
            on_click=on_click,
            bgcolor=AppTheme.DANGER,
            color="#ffffff",
            style=style,
        )
    return ft.OutlinedButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=AppTheme.DANGER,
            bgcolor=AppTheme.SURFACE_ELEVATED,
            shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_MD),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            side=ft.BorderSide(1, AppTheme.DANGER_SOFT),
        ),
    )


def stat_card(label: str, value_control: ft.Control, accent: str, icon: str) -> ft.Container:
    return ft.Container(
        expand=True,
        padding=ft.padding.symmetric(horizontal=14, vertical=12),
        border_radius=AppTheme.RADIUS_LG,
        bgcolor=AppTheme.SURFACE_ELEVATED,
        border=ft.border.all(1, AppTheme.BORDER),
        content=ft.Row(
            spacing=10,
            controls=[
                ft.Container(
                    width=40,
                    height=40,
                    border_radius=AppTheme.RADIUS_MD,
                    bgcolor=ft.colors.with_opacity(0.15, accent),
                    alignment=ft.alignment.center,
                    content=ft.Icon(icon, size=20, color=accent),
                ),
                ft.Column(
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(label, size=AppTheme.FONT_CAPTION, color=AppTheme.TEXT_MUTED),
                        value_control,
                    ],
                ),
            ],
        ),
    )


def section_title(text: str, icon: str, accent: str) -> ft.Row:
    return ft.Row(
        spacing=8,
        controls=[
            ft.Icon(icon, size=18, color=accent),
            ft.Text(text, size=AppTheme.FONT_HEADING, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
        ],
    )


def card_button(label: str, on_click, *, variant: str = "default", width: int | None = None) -> ft.Control:
    """Nút nhỏ trong card kết quả (legacy)."""

    kwargs: dict = {"text": label, "on_click": on_click}
    if width is not None:
        kwargs["width"] = width
    style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_SM),
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        elevation=0,
    )
    if variant == "danger":
        return ft.ElevatedButton(**kwargs, bgcolor=AppTheme.DANGER_SOFT, color=AppTheme.DANGER, style=style)
    if variant == "outline":
        return ft.OutlinedButton(
            **kwargs,
            style=ft.ButtonStyle(
                color=AppTheme.TEXT_SECONDARY,
                shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_SM),
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                side=ft.BorderSide(1, AppTheme.BORDER),
            ),
        )
    return ft.ElevatedButton(**kwargs, bgcolor=AppTheme.SURFACE_ELEVATED, color=AppTheme.TEXT_PRIMARY, style=style)
