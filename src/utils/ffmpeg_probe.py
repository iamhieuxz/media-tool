"""FFmpeg ffprobe wrapper — metadata và validation video."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger("ffmpeg_probe")


@dataclass(slots=True)
class VideoProbeResult:
    """Metadata video từ ffprobe."""

    valid: bool
    duration_sec: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    error: str | None = None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def probe_video(path: Path) -> VideoProbeResult | None:
    """Chạy ffprobe; trả None nếu ffprobe không cài."""

    if not ffprobe_available():
        return None

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("ffprobe thất bại %s: %s", path, exc)
        return VideoProbeResult(valid=False, error=str(exc))

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return VideoProbeResult(valid=False, error=detail or f"ffprobe exit {completed.returncode}")

    try:
        data = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        return VideoProbeResult(valid=False, error=f"Invalid ffprobe JSON: {exc}")

    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or 0)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)

    width = height = 0
    fps = 0.0
    codec = ""
    if video_stream:
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        codec = str(video_stream.get("codec_name") or "")
        rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/1"
        if isinstance(rate, str) and "/" in rate:
            num, den = rate.split("/", 1)
            try:
                fps = float(num) / float(den) if float(den) else 0.0
            except ValueError:
                fps = 0.0

    if duration <= 0 and not video_stream:
        return VideoProbeResult(valid=False, error="No video stream or zero duration")

    return VideoProbeResult(
        valid=True,
        duration_sec=duration,
        width=width,
        height=height,
        fps=round(fps, 2),
        codec=codec,
    )
