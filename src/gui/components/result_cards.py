"""Thẻ hiển thị kết quả quét."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.constants import MEDIA_TYPE_LABELS
from src.gui.theme import AppTheme, card_button


def _media_type_label(value: str) -> str:
    return MEDIA_TYPE_LABELS.get(value, value).upper()


def build_invalid_card(
    row: dict[str, str],
    on_open: Callable[[Path], None],
    on_open_folder: Callable[[Path], None],
) -> ft.Container:
    """Tạo card hiển thị một file lỗi."""

    path = Path(row["path"])
    return ft.Container(
        padding=14,
        border_radius=AppTheme.RADIUS_LG,
        bgcolor=AppTheme.SURFACE_CARD,
        border=ft.border.all(1, AppTheme.BORDER),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=AppTheme.RADIUS_SM,
                            bgcolor=AppTheme.DANGER_SOFT,
                            content=ft.Text("LỖI", size=10, weight=ft.FontWeight.BOLD, color=AppTheme.DANGER),
                        ),
                        ft.Text(_media_type_label(row["media_type"]), size=10, color=AppTheme.TEXT_MUTED),
                    ],
                ),
                ft.Text(
                    row["path"],
                    size=AppTheme.FONT_BODY,
                    weight=ft.FontWeight.W_500,
                    selectable=True,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    color=AppTheme.TEXT_PRIMARY,
                ),
                ft.Text(row["error"], size=AppTheme.FONT_CAPTION, color=AppTheme.DANGER, selectable=True),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        card_button("Mở file", on_click=lambda _e, p=path: on_open(p)),
                        card_button("Mở thư mục", on_click=lambda _e, p=path: on_open_folder(p.parent), variant="outline"),
                    ],
                ),
            ],
        ),
    )


def build_duplicate_card(
    row: dict[str, Any],
    on_open: Callable[[Path], None],
    on_open_folder: Callable[[Path], None],
    on_delete_duplicate: Callable[[Path], None],
) -> ft.Container:
    """Tạo card hiển thị một nhóm file trùng lặp."""

    paths = [Path(item) for item in row.get("paths", []) if isinstance(item, str)]
    path_cards: list[ft.Control] = []
    for index, path in enumerate(paths):
        is_keep = index == 0
        badge_text = "GIỮ" if is_keep else "LẶP"
        badge_bg = AppTheme.SUCCESS_SOFT if is_keep else AppTheme.DUPLICATE_SOFT
        badge_color = AppTheme.SUCCESS if is_keep else AppTheme.DUPLICATE

        path_cards.append(
            ft.Container(
                padding=12,
                border_radius=AppTheme.RADIUS_MD,
                bgcolor=AppTheme.SURFACE_ELEVATED if is_keep else AppTheme.BG,
                border=ft.border.all(1, AppTheme.BORDER if not is_keep else f"{AppTheme.SUCCESS}44"),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            expand=True,
                            spacing=10,
                            controls=[
                                ft.Container(
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                    border_radius=AppTheme.RADIUS_SM,
                                    bgcolor=badge_bg,
                                    content=ft.Text(badge_text, size=10, weight=ft.FontWeight.BOLD, color=badge_color),
                                ),
                                ft.Text(
                                    str(path),
                                    expand=True,
                                    selectable=True,
                                    size=AppTheme.FONT_CAPTION,
                                    color=AppTheme.TEXT_PRIMARY if is_keep else AppTheme.TEXT_SECONDARY,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                        ),
                        ft.Row(
                            tight=True,
                            spacing=6,
                            controls=[
                                card_button("Mở", on_click=lambda _e, p=path: on_open(p), width=52),
                                card_button("Thư mục", on_click=lambda _e, p=path: on_open_folder(p.parent), variant="outline", width=72),
                                *(
                                    []
                                    if is_keep
                                    else [card_button("Xoá", on_click=lambda _e, p=path: on_delete_duplicate(p), variant="danger", width=52)]
                                ),
                            ],
                        ),
                    ],
                ),
            )
        )

    return ft.Container(
        padding=14,
        border_radius=AppTheme.RADIUS_LG,
        bgcolor=AppTheme.SURFACE_CARD,
        border=ft.border.all(1, AppTheme.BORDER),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    spacing=16,
                    controls=[
                        ft.Text(
                            f"{row['size']:,} byte",
                            size=AppTheme.FONT_BODY,
                            weight=ft.FontWeight.W_600,
                            color=AppTheme.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            f"Mã băm: {row['hash_value']}",
                            size=AppTheme.FONT_CAPTION,
                            color=AppTheme.TEXT_MUTED,
                            selectable=True,
                        ),
                    ],
                ),
                *path_cards,
            ],
        ),
    )
