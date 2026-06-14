"""Engine băm file — SHA256 (Level 1) và interface cho các level cao hơn."""

from __future__ import annotations

import enum
from hashlib import md5, sha256
from pathlib import Path
from typing import Protocol

from src.constants import IO_CHUNK_SIZE
from src.utils.logging_config import get_logger

logger = get_logger("hash_engine")


class HashLevel(enum.IntEnum):
    """Mức độ phát hiện trùng lặp."""

    EXACT_MD5 = 0  # Legacy — tương thích ngược
    EXACT_SHA256 = 1
    PERCEPTUAL = 2
    VIDEO_SIMILARITY = 3
    NEAR_DUPLICATE = 4


class HashEngineProtocol(Protocol):
    """Giao diện chung cho mọi engine băm."""

    def hash_file(self, path: Path) -> str: ...

    def partial_hash(self, path: Path, size: int) -> str: ...


class HashEngine:
    """Băm file nội dung — SHA256 mặc định, MD5 legacy."""

    def __init__(self, level: HashLevel = HashLevel.EXACT_SHA256) -> None:
        self.level = level

    def _digest_name(self) -> str:
        if self.level == HashLevel.EXACT_MD5:
            return "md5"
        return "sha256"

    def _new_digest(self):
        if self.level == HashLevel.EXACT_MD5:
            return md5()
        return sha256()

    def hash_file(self, path: Path) -> str:
        """Băm toàn bộ nội dung file."""

        digest = self._new_digest()
        with path.open("rb") as file:
            while True:
                chunk = file.read(IO_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def partial_hash(self, path: Path, size: int) -> str:
        """Băm nhanh đầu/cuối file để loại trừ trước khi đọc toàn bộ."""

        digest = self._new_digest()
        with path.open("rb") as file:
            digest.update(file.read(IO_CHUNK_SIZE))
            if size > IO_CHUNK_SIZE * 2:
                file.seek(size - IO_CHUNK_SIZE)
                digest.update(file.read(IO_CHUNK_SIZE))
            elif size > IO_CHUNK_SIZE:
                file.seek(IO_CHUNK_SIZE)
                digest.update(file.read())
        return digest.hexdigest()

    @property
    def algorithm_label(self) -> str:
        return self._digest_name().upper()
