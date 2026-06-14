"""Kiểm tra file media bị lỗi cho ảnh và video — multi-layer validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import cv2
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

try:
    from PIL import Image, UnidentifiedImageError
except ModuleNotFoundError:  # pragma: no cover
    Image = None  # type: ignore[assignment]
    UnidentifiedImageError = OSError  # type: ignore[assignment,misc]

from src.constants import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from src.utils.ffmpeg_probe import probe_video
from src.utils.logging_config import get_logger

logger = get_logger("checker")

IMAGE_EXTENSIONS = set(IMAGE_EXTENSIONS)
VIDEO_EXTENSIONS = set(VIDEO_EXTENSIONS)


@dataclass(slots=True)
class MediaCheckResult:
    """Kết quả kiểm tra một file media."""

    path: Path
    is_valid: bool
    media_type: str
    error: str | None = None
    severity: str = "valid"
    resolution: str = ""
    width: int = 0
    height: int = 0
    duration_sec: float = 0.0
    fps: float = 0.0
    codec: str = ""


class MediaChecker:
    """Kiểm tra ảnh và video bị hỏng — PIL, OpenCV, ffprobe."""

    def __init__(
        self,
        image_extensions: Iterable[str] | None = None,
        video_extensions: Iterable[str] | None = None,
    ) -> None:
        self.image_extensions = {ext.lower() for ext in (image_extensions or IMAGE_EXTENSIONS)}
        self.video_extensions = {ext.lower() for ext in (video_extensions or VIDEO_EXTENSIONS)}

    def check(self, path: Path) -> MediaCheckResult:
        suffix = path.suffix.lower()
        if suffix in self.image_extensions:
            return self._check_image(path)
        if suffix in self.video_extensions:
            return self._check_video(path)
        return MediaCheckResult(path=path, is_valid=True, media_type="không xác định")

    def _check_image(self, path: Path) -> MediaCheckResult:
        if Image is None:
            return MediaCheckResult(
                path=path,
                is_valid=False,
                media_type="ảnh",
                error="Thiếu thư viện Pillow để kiểm tra ảnh.",
                severity="major",
            )

        width = height = 0
        issues: list[tuple[str, str]] = []

        # Layer 1: PIL verify + load
        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                img.load()
                width, height = img.size
                # Layer 3: metadata / EXIF
                if hasattr(img, "getexif"):
                    try:
                        exif = img.getexif()
                        if exif and len(exif) == 0 and path.stat().st_size > 512:
                            issues.append(("Empty EXIF on large file", "minor"))
                    except OSError as exc:
                        issues.append((f"EXIF read error: {exc}", "minor"))
        except (OSError, UnidentifiedImageError) as exc:
            logger.debug("PIL ảnh lỗi %s: %s", path, exc)
            return MediaCheckResult(
                path=path,
                is_valid=False,
                media_type="ảnh",
                error=str(exc),
                severity="unreadable",
            )

        # Layer 2: OpenCV decode
        if cv2 is not None and np is not None:
            try:
                raw = np.fromfile(path, dtype=np.uint8)
                decoded = cv2.imdecode(raw, cv2.IMREAD_COLOR)
                if decoded is None:
                    issues.append(("OpenCV cannot decode image", "major"))
            except OSError as exc:
                issues.append((f"OpenCV decode error: {exc}", "minor"))

        return self._finalize("ảnh", path, width, height, issues)

    def _check_video(self, path: Path) -> MediaCheckResult:
        issues: list[tuple[str, str]] = []
        width = height = 0
        duration = 0.0
        fps = 0.0
        codec = ""

        # Layer 1: ffprobe
        probe = probe_video(path)
        if probe is not None:
            if not probe.valid:
                return MediaCheckResult(
                    path=path,
                    is_valid=False,
                    media_type="video",
                    error=probe.error or "ffprobe validation failed",
                    severity="unreadable",
                )
            width, height = probe.width, probe.height
            duration, fps, codec = probe.duration_sec, probe.fps, probe.codec
            if duration <= 0:
                issues.append(("Zero or missing duration", "major"))
            if width <= 0 or height <= 0:
                issues.append(("Missing video dimensions", "major"))
        elif cv2 is None:
            return MediaCheckResult(
                path=path,
                is_valid=False,
                media_type="video",
                error="Thiếu OpenCV/ffprobe để kiểm tra video.",
                severity="major",
            )

        # Layer 2: OpenCV open + read frame + header
        if cv2 is not None:
            cap = cv2.VideoCapture(str(path))
            try:
                if not cap.isOpened():
                    issues.append(("Cannot open video (header damaged?)", "unreadable"))
                else:
                    if width <= 0:
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                    if height <= 0:
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                    if fps <= 0:
                        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        issues.append(("Cannot read first video frame", "unreadable"))
                    elif duration <= 0 and fps > 0:
                        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                        if frames > 0:
                            duration = frames / fps
            except OSError as exc:
                issues.append((str(exc), "major"))
            finally:
                cap.release()

        result = self._finalize("video", path, width, height, issues)
        result.duration_sec = duration
        result.fps = fps
        result.codec = codec
        return result

    def _finalize(
        self,
        media_type: str,
        path: Path,
        width: int,
        height: int,
        issues: list[tuple[str, str]],
    ) -> MediaCheckResult:
        resolution = f"{width}x{height}" if width > 0 and height > 0 else ""

        if not issues:
            return MediaCheckResult(
                path=path,
                is_valid=True,
                media_type=media_type,
                severity="valid",
                resolution=resolution,
                width=width,
                height=height,
            )

        severity_order = ["unreadable", "major", "minor"]
        worst = "minor"
        for _, sev in issues:
            if severity_order.index(sev) < severity_order.index(worst):
                worst = sev

        error_text = "; ".join(msg for msg, _ in issues)
        is_valid = worst == "minor"

        return MediaCheckResult(
            path=path,
            is_valid=is_valid,
            media_type=media_type,
            error=error_text,
            severity=worst if not is_valid else "minor",
            resolution=resolution,
            width=width,
            height=height,
        )
