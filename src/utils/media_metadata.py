"""Trích xuất metadata ảnh/video — resolution, duration, codec."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import cv2
except ModuleNotFoundError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover
    Image = None  # type: ignore[assignment]

from src.constants import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from src.utils.ffmpeg_probe import probe_video
from src.utils.logging_config import get_logger

logger = get_logger("media_metadata")


@dataclass(slots=True)
class MediaMetadata:
    """Metadata hiển thị cho preview và bảng kết quả."""

    path: Path
    width: int = 0
    height: int = 0
    duration_sec: float = 0.0
    fps: float = 0.0
    codec: str = ""
    file_size: int = 0

    @property
    def resolution(self) -> str:
        if self.width > 0 and self.height > 0:
            return f"{self.width}x{self.height}"
        return "—"

    @property
    def duration_label(self) -> str:
        if self.duration_sec <= 0:
            return "—"
        mins, secs = divmod(int(self.duration_sec), 60)
        return f"{mins}:{secs:02d}"


def extract_metadata(path: Path) -> MediaMetadata:
    """Lấy metadata cơ bản cho file media."""

    try:
        file_size = path.stat().st_size
    except OSError:
        file_size = 0

    suffix = path.suffix.lower()
    meta = MediaMetadata(path=path, file_size=file_size)

    if suffix in IMAGE_EXTENSIONS:
        meta = _image_metadata(path, meta)
    elif suffix in VIDEO_EXTENSIONS:
        meta = _video_metadata(path, meta)
    return meta


def _image_metadata(path: Path, meta: MediaMetadata) -> MediaMetadata:
    if Image is None:
        return meta
    try:
        with Image.open(path) as img:
            meta.width, meta.height = img.size
    except OSError as exc:
        logger.debug("Không đọc metadata ảnh %s: %s", path, exc)
    return meta


def _video_metadata(path: Path, meta: MediaMetadata) -> MediaMetadata:
    probe = probe_video(path)
    if probe is not None and probe.valid:
        meta.width = probe.width
        meta.height = probe.height
        meta.duration_sec = probe.duration_sec
        meta.fps = probe.fps
        meta.codec = probe.codec
        return meta

    if cv2 is None:
        return meta
    cap = cv2.VideoCapture(str(path))
    try:
        if cap.isOpened():
            meta.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            meta.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            meta.fps = round(float(cap.get(cv2.CAP_PROP_FPS) or 0), 2)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if meta.fps > 0 and frames > 0:
                meta.duration_sec = frames / meta.fps
    except OSError as exc:
        logger.debug("OpenCV metadata %s: %s", path, exc)
    finally:
        cap.release()
    return meta
