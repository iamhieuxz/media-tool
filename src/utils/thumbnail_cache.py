"""Cache thumbnail cho preview và bảng kết quả."""

from __future__ import annotations

import hashlib
from pathlib import Path

try:
    import cv2
except ModuleNotFoundError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover
    Image = None  # type: ignore[assignment]

from src.constants import IMAGE_EXTENSIONS, THUMBNAIL_CACHE_DIR, VIDEO_EXTENSIONS
from src.utils.logging_config import get_logger

logger = get_logger("thumbnail_cache")

THUMB_SIZE = (96, 96)
VIDEO_THUMB_FRAME = 0


class ThumbnailCache:
    """Sinh và lưu thumbnail trên đĩa (data/thumbnails/)."""

    def __init__(self, cache_dir: Path | str = THUMBNAIL_CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, path: Path, mtime: float) -> str:
        digest = hashlib.sha256(f"{path.resolve()}:{mtime}".encode()).hexdigest()
        return digest[:24]

    def _thumb_path(self, path: Path, mtime: float) -> Path:
        return self.cache_dir / f"{self._cache_key(path, mtime)}.jpg"

    def get_thumbnail(self, media_path: Path) -> Path | None:
        """Trả path thumbnail JPG; sinh mới nếu chưa có."""

        if not media_path.is_file():
            return None
        try:
            mtime = media_path.stat().st_mtime
        except OSError:
            return None

        dest = self._thumb_path(media_path, mtime)
        if dest.exists():
            return dest

        suffix = media_path.suffix.lower()
        try:
            if suffix in IMAGE_EXTENSIONS:
                ok = self._generate_image_thumb(media_path, dest)
            elif suffix in VIDEO_EXTENSIONS:
                ok = self._generate_video_thumb(media_path, dest)
            else:
                return None
            return dest if ok and dest.exists() else None
        except OSError as exc:
            logger.debug("Thumbnail thất bại %s: %s", media_path, exc)
            return None

    def _generate_image_thumb(self, source: Path, dest: Path) -> bool:
        if Image is None:
            return False
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            img.save(dest, "JPEG", quality=82)
        return True

    def _generate_video_thumb(self, source: Path, dest: Path) -> bool:
        if cv2 is None or Image is None:
            return False
        cap = cv2.VideoCapture(str(source))
        try:
            if not cap.isOpened():
                return False
            cap.set(cv2.CAP_PROP_POS_FRAMES, VIDEO_THUMB_FRAME)
            ok, frame = cap.read()
            if not ok or frame is None:
                return False
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            img.save(dest, "JPEG", quality=82)
            return True
        finally:
            cap.release()

    def clear(self) -> None:
        for file in self.cache_dir.glob("*.jpg"):
            try:
                file.unlink()
            except OSError:
                pass
