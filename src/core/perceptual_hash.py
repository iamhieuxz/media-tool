"""Perceptual hash cho ảnh — pHash và dHash (Level 2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import imagehash
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover
    imagehash = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]

from src.utils.logging_config import get_logger

logger = get_logger("perceptual_hash")


@dataclass(slots=True)
class PerceptualHashResult:
    """Kết quả băm cảm quan cho một ảnh."""

    path: Path
    phash: str
    dhash: str


class PerceptualHashEngine:
    """Tính pHash và dHash cho ảnh."""

    def __init__(self) -> None:
        self._available = imagehash is not None and Image is not None

    @property
    def is_available(self) -> bool:
        return self._available

    def compute(self, path: Path) -> PerceptualHashResult | None:
        """Tính pHash và dHash; trả None nếu thiếu thư viện hoặc file lỗi."""

        if not self._available:
            logger.debug("Thiếu imagehash/Pillow — bỏ qua perceptual hash cho %s", path)
            return None
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                ph = str(imagehash.phash(img))
                dh = str(imagehash.dhash(img))
            return PerceptualHashResult(path=path, phash=ph, dhash=dh)
        except OSError as exc:
            logger.debug("Không tính được perceptual hash %s: %s", path, exc)
            return None

    @staticmethod
    def hamming_distance(hash_a: str, hash_b: str) -> int:
        """Khoảng cách Hamming giữa hai chuỗi hash hex."""

        if len(hash_a) != len(hash_b):
            return max(len(hash_a), len(hash_b)) * 4
        distance = 0
        for a, b in zip(hash_a, hash_b, strict=True):
            distance += bin(int(a, 16) ^ int(b, 16)).count("1")
        return distance

    def compute_from_array(self, bgr_array: object) -> str | None:
        """Tính pHash từ mảng OpenCV BGR (dùng cho video frame)."""

        if not self._available:
            return None
        try:
            import cv2  # noqa: PLC0415 — import tùy chọn

            rgb = cv2.cvtColor(bgr_array, cv2.COLOR_BGR2RGB)  # type: ignore[arg-type]
            img = Image.fromarray(rgb)
            return str(imagehash.phash(img))
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("Không tính pHash từ array: %s", exc)
            return None

    @staticmethod
    def similarity_percent(hash_a: str, hash_b: str, bits: int = 64) -> float:
        """Phần trăm tương đồng (0–100) dựa trên Hamming distance."""

        dist = PerceptualHashEngine.hamming_distance(hash_a, hash_b)
        return max(0.0, (1.0 - dist / bits) * 100.0)
