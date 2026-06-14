"""Helper hiển thị dialog xác nhận."""

from __future__ import annotations

from collections.abc import Callable

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.gui.theme import AppTheme, danger_button, secondary_button


def close_dialog(page: ft.Page) -> None:
    """Đóng dialog hiện tại."""

    if page.dialog:
        page.dialog.open = False
        page.update()


def show_confirm_dialog(
    page: ft.Page,
    title: str,
    content: str,
    confirm_label: str,
    on_confirm: Callable[[ft.ControlEvent], None],
) -> None:
    """Hiển thị dialog xác nhận với nút Huỷ và nút xác nhận."""

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=AppTheme.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=AppTheme.RADIUS_LG),
        title=ft.Text(title, color=AppTheme.TEXT_PRIMARY, weight=ft.FontWeight.W_600),
        content=ft.Text(content, color=AppTheme.TEXT_SECONDARY, size=AppTheme.FONT_BODY),
        actions=[
            secondary_button("Huỷ", ft.icons.CLOSE, lambda _e: close_dialog(page)),
            danger_button(confirm_label, ft.icons.DELETE_FOREVER, on_confirm, filled=True),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.dialog = dialog
    dialog.open = True
    page.update()
