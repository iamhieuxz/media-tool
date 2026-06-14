"""Preview panel — mockup sidebar phải."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

try:
    import flet as ft
except ModuleNotFoundError:  # pragma: no cover
    ft = None  # type: ignore[assignment]

from src.constants import PREVIEW_IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from src.gui.theme import AppTheme, ghost_button, glass_panel
from src.utils.media_metadata import MediaMetadata, extract_metadata
from src.utils.thumbnail_cache import ThumbnailCache

FitMode = Literal["contain", "cover", "fill"]


@dataclass
class PreviewControls:
    container: ft.Container
    preview_stack: ft.Stack
    preview_image: ft.Image
    compare_left: ft.Image
    compare_right: ft.Image
    single_view: ft.Container
    compare_view: ft.Row
    filename_label: ft.Text
    meta_label: ft.Text
    detail_label: ft.Text
    placeholder: ft.Container
    _zoom: float = 1.0
    _thumb_cache: ThumbnailCache = field(default_factory=ThumbnailCache)

    def set_thumbnail_cache(self, cache: ThumbnailCache) -> None:
        self._thumb_cache = cache

    def show_file(
        self,
        path: Path | None,
        *,
        size: int = 0,
        resolution: str = "",
        metadata: MediaMetadata | None = None,
    ) -> None:
        self.compare_view.visible = False
        self.single_view.visible = False
        self.preview_image.visible = False

        if path is None or not path.exists():
            self.placeholder.visible = True
            self.filename_label.value = "—"
            self.meta_label.value = "Select a file to preview"
            self.detail_label.value = ""
            return

        meta = metadata or extract_metadata(path)
        if not resolution and meta.resolution != "—":
            resolution = meta.resolution
        if size <= 0:
            size = meta.file_size

        self.filename_label.value = path.name
        self.meta_label.value = f"{_format_size(size)} · {resolution}"
        self.detail_label.value = _format_details(path, meta)

        thumb = self._thumb_cache.get_thumbnail(path)
        src = str(thumb or path.resolve())
        suffix = path.suffix.lower()

        if suffix in PREVIEW_IMAGE_EXTENSIONS or suffix in VIDEO_EXTENSIONS or thumb:
            self._apply_image(self.preview_image, src)
            self.preview_image.visible = True
            self.single_view.visible = True
            self.placeholder.visible = False
        else:
            self.placeholder.visible = True

    def set_compare(self, path_a: Path | None, path_b: Path | None) -> None:
        if path_a is None or path_b is None or not path_a.exists() or not path_b.exists():
            self.compare_view.visible = False
            return
        thumb_a = self._thumb_cache.get_thumbnail(path_a)
        thumb_b = self._thumb_cache.get_thumbnail(path_b)
        self._apply_image(self.compare_left, str(thumb_a or path_a.resolve()))
        self._apply_image(self.compare_right, str(thumb_b or path_b.resolve()))
        self.single_view.visible = False
        self.placeholder.visible = False
        self.compare_view.visible = True
        self.filename_label.value = f"{path_a.name}  vs  {path_b.name}"
        self.meta_label.value = "Comparison view"
        self.detail_label.value = ""

    def set_fit_mode(self, mode: FitMode) -> None:
        fit_map = {"contain": ft.ImageFit.CONTAIN, "cover": ft.ImageFit.COVER, "fill": ft.ImageFit.FILL}
        fit = fit_map.get(mode, ft.ImageFit.CONTAIN)
        for img in (self.preview_image, self.compare_left, self.compare_right):
            img.fit = fit

    def zoom(self, delta: float) -> None:
        self._zoom = max(0.5, min(3.0, self._zoom + delta))
        h = int(200 * self._zoom)
        for img in (self.preview_image, self.compare_left, self.compare_right):
            img.height = h

    def _apply_image(self, control: ft.Image, src: str) -> None:
        control.src = src
        control.height = int(200 * self._zoom)
        control.fit = ft.ImageFit.CONTAIN


def _format_size(size: int) -> str:
    if size >= 1_048_576:
        return f"{size / 1_048_576:.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _format_details(path: Path, meta: MediaMetadata) -> str:
    if path.suffix.lower() in VIDEO_EXTENSIONS:
        parts = [f"Duration: {meta.duration_label}"]
        if meta.fps > 0:
            parts.append(f"FPS: {meta.fps}")
        if meta.codec:
            parts.append(f"Codec: {meta.codec}")
        return " · ".join(parts)
    return ""


def build_preview_panel(
    *,
    on_fit: Callable[[ft.ControlEvent], None] | None = None,
    on_zoom_in: Callable[[ft.ControlEvent], None] | None = None,
    on_zoom_out: Callable[[ft.ControlEvent], None] | None = None,
    on_compare: Callable[[ft.ControlEvent], None] | None = None,
) -> PreviewControls:
    preview_image = ft.Image(
        visible=False,
        fit=ft.ImageFit.CONTAIN,
        border_radius=AppTheme.RADIUS_MD,
        height=200,
    )
    compare_left = ft.Image(fit=ft.ImageFit.CONTAIN, border_radius=AppTheme.RADIUS_MD, height=200, expand=True)
    compare_right = ft.Image(fit=ft.ImageFit.CONTAIN, border_radius=AppTheme.RADIUS_MD, height=200, expand=True)
    placeholder = ft.Container(
        height=200,
        border_radius=AppTheme.RADIUS_MD,
        bgcolor=AppTheme.SURFACE_ELEVATED,
        border=ft.border.all(1, AppTheme.BORDER),
        alignment=ft.alignment.center,
        content=ft.Icon(ft.icons.IMAGE_OUTLINED, size=40, color=AppTheme.TEXT_MUTED),
    )
    single_view = ft.Container(
        content=preview_image,
        border_radius=AppTheme.RADIUS_MD,
        border=ft.border.all(1, AppTheme.BORDER),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    compare_view = ft.Row(
        visible=False,
        spacing=6,
        controls=[
            ft.Container(expand=True, content=compare_left, border_radius=AppTheme.RADIUS_MD, clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
            ft.Container(expand=True, content=compare_right, border_radius=AppTheme.RADIUS_MD, clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
        ],
    )
    preview_stack = ft.Stack(controls=[placeholder, single_view, compare_view])

    filename_label = ft.Text("—", size=AppTheme.FONT_BODY, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY)
    meta_label = ft.Text("Select a file to preview", size=AppTheme.FONT_CAPTION, color=AppTheme.TEXT_MUTED)
    detail_label = ft.Text("", size=AppTheme.FONT_CAPTION, color=AppTheme.TEXT_SECONDARY)

    controls = PreviewControls(
        container=ft.Container(),
        preview_stack=preview_stack,
        preview_image=preview_image,
        compare_left=compare_left,
        compare_right=compare_right,
        single_view=single_view,
        compare_view=compare_view,
        filename_label=filename_label,
        meta_label=meta_label,
        detail_label=detail_label,
        placeholder=placeholder,
    )

    container = glass_panel(
        ft.Column(
            spacing=10,
            controls=[
                ft.Text("Preview Panel", size=AppTheme.FONT_HEADING, weight=ft.FontWeight.W_600, color=AppTheme.TEXT_PRIMARY),
                preview_stack,
                filename_label,
                meta_label,
                detail_label,
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.Dropdown(
                            value="fit",
                            width=140,
                            dense=True,
                            options=[
                                ft.dropdown.Option("fit", "Comparison view"),
                                ft.dropdown.Option("contain", "Fit screen"),
                            ],
                            border_color=AppTheme.BORDER,
                            bgcolor=AppTheme.SURFACE_ELEVATED,
                            text_style=ft.TextStyle(size=11, color=AppTheme.TEXT_SECONDARY),
                        ),
                        ghost_button("", ft.icons.FIT_SCREEN, on_fit or (lambda _e: None)),
                        ghost_button("", ft.icons.COMPARE, on_compare or (lambda _e: None)),
                        ghost_button("", ft.icons.DELETE_OUTLINE, lambda _e: None),
                    ],
                ),
            ],
        ),
        padding=12,
    )
    controls.container = container
    return controls
