"""Hằng số dùng chung cho toàn bộ ứng dụng."""

from __future__ import annotations

APP_TITLE = "Media Scanner Pro"
APP_SUBTITLE = "Quét media · phát hiện file lỗi · tìm và xoá trùng lặp"

# Thư mục lưu trữ
LOGS_DIR = "logs"
SCAN_HISTORY_DIR = "scan_history"
DATA_DIR = "data"

MEDIA_TYPE_LABELS: dict[str, str] = {
    "image": "Ảnh",
    "video": "Video",
    "unknown": "Không xác định",
    "ảnh": "Ảnh",
    "không xác định": "Không xác định",
}

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
)
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
)
MEDIA_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
PREVIEW_IMAGE_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS

INVALID_MEDIA_CSV = "invalid_media.csv"
DUPLICATE_MEDIA_CSV = "duplicate_media.csv"
INVALID_MEDIA_BUCKET = "invalid_media_bucket"
QUARANTINE_DIR = "quarantine"
THUMBNAIL_CACHE_DIR = "data/thumbnails"

# Kích thước buffer đọc file (64 KiB)
IO_CHUNK_SIZE = 65536

# Tối thiểu giữa hai lần vẽ lại giao diện (giây)
UI_UPDATE_INTERVAL_SEC = 0.15
