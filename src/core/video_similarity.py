"""So sánh video qua frame mẫu (Level 3) — foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import cv2
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

from src.core.perceptual_hash import PerceptualHashEngine
from src.utils.logging_config import get_logger

logger = get_logger("video_similarity")

# Vị trí lấy frame mẫu: 0%, 25%, 50%, 75%, 100%
SAMPLE_POSITIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass(slots=True)
class VideoFrameSample:
    """Một frame mẫu kèm hash."""

    position: float
    phash: str
    histogram: list[float] = field(default_factory=list)


@dataclass(slots=True)
class VideoSignature:
    """Chữ ký video từ các frame mẫu."""

    path: Path
    frames: list[VideoFrameSample] = field(default_factory=list)
    duration_sec: float = 0.0
    fps: float = 0.0
    width: int = 0
    height: int = 0


class VideoSimilarityEngine:
    """Trích xuất frame mẫu và so sánh video."""

    def __init__(self) -> None:
        self._phash = PerceptualHashEngine()
        self._available = cv2 is not None and np is not None

    @property
    def is_available(self) -> bool:
        return self._available

    def extract_signature(self, path: Path) -> VideoSignature | None:
        """Lấy frame tại 0/25/50/75/100% và tính pHash + histogram."""

        if not self._available:
            return None

        cap = cv2.VideoCapture(str(path))
        try:
            if not cap.isOpened():
                return None

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            duration = total_frames / fps if fps > 0 else 0.0

            frames: list[VideoFrameSample] = []
            for pos in SAMPLE_POSITIONS:
                if total_frames > 1:
                    frame_idx = int(pos * (total_frames - 1))
                else:
                    frame_idx = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
                hist_norm = (hist.flatten() / max(hist.sum(), 1)).tolist()
                ph_result = self._phash.compute_from_array(frame)
                frames.append(
                    VideoFrameSample(
                        position=pos,
                        phash=ph_result or "",
                        histogram=hist_norm[:64],
                    )
                )

            return VideoSignature(
                path=path,
                frames=frames,
                duration_sec=duration,
                fps=fps,
                width=width,
                height=height,
            )
        except OSError as exc:
            logger.debug("Không trích xuất được signature %s: %s", path, exc)
            return None
        finally:
            cap.release()

    def compare(self, sig_a: VideoSignature, sig_b: VideoSignature) -> float:
        """Phần trăm tương đồng trung bình giữa hai video (0–100)."""

        if not sig_a.frames or not sig_b.frames:
            return 0.0
        scores: list[float] = []
        for fa, fb in zip(sig_a.frames, sig_b.frames):
            if fa.phash and fb.phash:
                scores.append(PerceptualHashEngine.similarity_percent(fa.phash, fb.phash))
        return sum(scores) / len(scores) if scores else 0.0
