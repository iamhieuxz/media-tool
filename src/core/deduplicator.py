"""Tìm file trùng lặp — exact hash (SHA256/MD5) và perceptual (pHash/dHash)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from src.constants import IMAGE_EXTENSIONS
from src.core.hash_engine import HashEngine, HashLevel
from src.core.perceptual_hash import PerceptualHashEngine, PerceptualHashResult
from src.db.database import Database
from src.utils.concurrency import io_worker_count
from src.utils.logging_config import get_logger

logger = get_logger("deduplicator")

PHASH_BITS = 64


@dataclass(slots=True)
class DuplicateResult:
    """Kết quả phát hiện nhóm file trùng lặp."""

    size: int
    hash_value: str
    paths: list[Path] = field(default_factory=list)
    match_type: str = "exact"  # exact | perceptual
    similarity: float = 100.0
    path_similarities: dict[str, float] = field(default_factory=dict)


class DuplicateFinder:
    """Tìm file trùng lặp theo level: exact (size→hash) hoặc perceptual (pHash)."""

    def __init__(
        self,
        hash_level: HashLevel = HashLevel.EXACT_SHA256,
        similarity_threshold: float = 95.0,
        hash_engine: HashEngine | None = None,
        perceptual_engine: PerceptualHashEngine | None = None,
        db: Database | None = None,
        worker_count: int = 0,
    ) -> None:
        self.hash_level = hash_level
        self.similarity_threshold = similarity_threshold
        self.worker_count = worker_count
        exact_level = hash_level if hash_level in (HashLevel.EXACT_MD5, HashLevel.EXACT_SHA256) else HashLevel.EXACT_SHA256
        self.hash_engine = hash_engine or HashEngine(level=exact_level)
        self.perceptual_engine = perceptual_engine or PerceptualHashEngine()
        self.db = db

    def _workers(self, total: int) -> int:
        return min(io_worker_count(self.worker_count), total) if total else 1

    def group_by_size(
        self,
        paths: Iterable[Path],
        sizes: dict[Path, int] | None = None,
    ) -> dict[int, list[Path]]:
        groups: dict[int, list[Path]] = {}
        for path in paths:
            if sizes is not None:
                size = sizes.get(path)
                if size is None:
                    continue
            else:
                if not path.is_file():
                    continue
                try:
                    size = path.stat().st_size
                except OSError as exc:
                    logger.warning("Không đọc được size của %s: %s", path, exc)
                    continue
            groups.setdefault(size, []).append(path)
        return groups

    def partial_hash(self, path: Path, size: int) -> str:
        return self.hash_engine.partial_hash(path, size)

    def hash_file(self, path: Path, size: int | None = None) -> str:
        """Băm file, dùng cache SQLite nếu có."""

        if self.db is not None and size is not None:
            try:
                mtime = path.stat().st_mtime
                cached = self.db.get_cached_hash(path, size, mtime, int(self.hash_level))
                if cached:
                    return cached
            except OSError:
                pass

        digest = self.hash_engine.hash_file(path)

        if self.db is not None and size is not None:
            try:
                mtime = path.stat().st_mtime
                self.db.store_hash(path, size, mtime, digest, int(self.hash_level))
            except OSError:
                pass
        return digest

    def _hash_group_parallel(
        self,
        paths: list[Path],
        size: int,
        executor: ThreadPoolExecutor,
        should_stop: Callable[[], bool] | None,
    ) -> dict[str, list[Path]]:
        hashes: dict[str, list[Path]] = {}

        def _hash_one(path: Path) -> tuple[Path, str]:
            return path, self.hash_file(path, size)

        futures = {executor.submit(_hash_one, path): path for path in paths}
        for future in as_completed(futures):
            if should_stop is not None and should_stop():
                for pending in futures:
                    pending.cancel()
                break
            path = futures[future]
            try:
                _, file_hash = future.result()
            except OSError as exc:
                logger.warning("Không hash được file %s: %s", path, exc)
                continue
            hashes.setdefault(file_hash, []).append(path)
        return hashes

    def _find_exact_duplicates(
        self,
        path_list: list[Path],
        sizes: dict[Path, int],
        progress_callback: Callable[[int, int], None] | None,
        should_stop: Callable[[], bool] | None,
    ) -> list[DuplicateResult]:
        results: list[DuplicateResult] = []
        groups = self.group_by_size(path_list, sizes=sizes)
        total_candidates = sum(len(candidates) for candidates in groups.values() if len(candidates) > 1)
        processed_candidates = 0
        workers = self._workers(total_candidates)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="hash") as executor:
            for size, candidates in groups.items():
                if should_stop is not None and should_stop():
                    break
                if len(candidates) < 2:
                    continue

                buckets: dict[str, list[Path]] = {}
                for candidate in candidates:
                    if should_stop is not None and should_stop():
                        return results
                    try:
                        key = self.partial_hash(candidate, size)
                    except OSError as exc:
                        logger.warning("Không hash một phần file %s: %s", candidate, exc)
                        processed_candidates += 1
                        if progress_callback is not None:
                            progress_callback(min(processed_candidates, total_candidates), total_candidates)
                        continue
                    buckets.setdefault(key, []).append(candidate)
                    processed_candidates += 1
                    if progress_callback is not None:
                        progress_callback(min(processed_candidates, total_candidates), total_candidates)

                for partial_group in buckets.values():
                    if len(partial_group) < 2:
                        continue
                    if should_stop is not None and should_stop():
                        return results

                    hashes = self._hash_group_parallel(partial_group, size, executor, should_stop)
                    algo = self.hash_engine.algorithm_label
                    for hash_value, grouped_paths in hashes.items():
                        existing = [p for p in grouped_paths if p.is_file()]
                        if len(existing) > 1:
                            results.append(
                                DuplicateResult(
                                    size=size,
                                    hash_value=f"{algo}:{hash_value}",
                                    paths=existing,
                                    match_type="exact",
                                    similarity=100.0,
                                )
                            )
        return results

    def _paths_in_exact_groups(self, groups: list[DuplicateResult]) -> set[Path]:
        covered: set[Path] = set()
        for group in groups:
            covered.update(group.paths)
        return covered

    def _find_perceptual_duplicates(
        self,
        image_paths: list[Path],
        exclude: set[Path],
        progress_callback: Callable[[int, int], None] | None,
        should_stop: Callable[[], bool] | None,
    ) -> list[DuplicateResult]:
        """Level 2 — nhóm ảnh tương tự qua pHash/dHash."""

        if not self.perceptual_engine.is_available:
            logger.warning("Perceptual hash không khả dụng — cài imagehash để dùng Level 2.")
            return []

        candidates = [p for p in image_paths if p not in exclude and p.suffix.lower() in IMAGE_EXTENSIONS]
        if len(candidates) < 2:
            return []

        hash_map: dict[Path, PerceptualHashResult] = {}
        total = len(candidates)
        completed = 0
        workers = self._workers(total)

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="phash") as executor:
            futures = {executor.submit(self.perceptual_engine.compute, path): path for path in candidates}
            for future in as_completed(futures):
                if should_stop is not None and should_stop():
                    for pending in futures:
                        pending.cancel()
                    break
                path = futures[future]
                try:
                    result = future.result()
                except OSError as exc:
                    logger.debug("pHash thất bại %s: %s", path, exc)
                    result = None
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, total)
                if result is not None:
                    hash_map[path] = result

        if len(hash_map) < 2:
            return []

        # Union-Find gom nhóm tương tự
        parent: dict[Path, Path] = {path: path for path in hash_map}

        def find(node: Path) -> Path:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(a: Path, b: Path) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        paths_list = list(hash_map.keys())
        threshold = self.similarity_threshold

        for i in range(len(paths_list)):
            if should_stop is not None and should_stop():
                return []
            for j in range(i + 1, len(paths_list)):
                pa, pb = paths_list[i], paths_list[j]
                sim_p = PerceptualHashEngine.similarity_percent(hash_map[pa].phash, hash_map[pb].phash, PHASH_BITS)
                sim_d = PerceptualHashEngine.similarity_percent(hash_map[pa].dhash, hash_map[pb].dhash, PHASH_BITS)
                sim = max(sim_p, sim_d)
                if sim >= threshold:
                    union(pa, pb)

        clusters: dict[Path, list[Path]] = {}
        for path in paths_list:
            root = find(path)
            clusters.setdefault(root, []).append(path)

        results: list[DuplicateResult] = []
        for members in clusters.values():
            if len(members) < 2:
                continue
            members.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            ref = members[0]
            ref_hash = hash_map[ref]
            sims: dict[str, float] = {}
            for member in members:
                sim_p = PerceptualHashEngine.similarity_percent(ref_hash.phash, hash_map[member].phash, PHASH_BITS)
                sim_d = PerceptualHashEngine.similarity_percent(ref_hash.dhash, hash_map[member].dhash, PHASH_BITS)
                sims[str(member)] = round(max(sim_p, sim_d), 1)

            try:
                max_size = max(m.stat().st_size for m in members if m.is_file())
            except OSError:
                max_size = 0

            avg_sim = sum(sims.values()) / len(sims)
            results.append(
                DuplicateResult(
                    size=max_size,
                    hash_value=f"pHash:{ref_hash.phash}",
                    paths=members,
                    match_type="perceptual",
                    similarity=round(avg_sim, 1),
                    path_similarities=sims,
                )
            )
        return results

    def find_duplicates(
        self,
        paths: Iterable[Path],
        progress_callback: Callable[[int, int], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
        sizes: dict[Path, int] | None = None,
        hash_level: HashLevel | None = None,
    ) -> list[DuplicateResult]:
        path_list = list(paths)
        level = hash_level or self.hash_level

        if sizes is None:
            sizes = {}
            for path in path_list:
                if path.is_file():
                    try:
                        sizes[path] = path.stat().st_size
                    except OSError:
                        continue

        results: list[DuplicateResult] = []

        # Level 1 — exact duplicate (SHA256 hoặc MD5)
        if level in (HashLevel.EXACT_MD5, HashLevel.EXACT_SHA256, HashLevel.PERCEPTUAL, HashLevel.VIDEO_SIMILARITY, HashLevel.NEAR_DUPLICATE):
            exact = self._find_exact_duplicates(path_list, sizes, progress_callback, should_stop)
            results.extend(exact)
            exact_paths = self._paths_in_exact_groups(exact)
        else:
            exact_paths = set()

        # Level 2 — perceptual (ảnh tương tự, kể cả khác size)
        if level in (HashLevel.PERCEPTUAL, HashLevel.NEAR_DUPLICATE):
            image_paths = [p for p in path_list if p.suffix.lower() in IMAGE_EXTENSIONS]

            def _perceptual_progress(done: int, total: int) -> None:
                if progress_callback is not None:
                    progress_callback(done, total)

            perceptual = self._find_perceptual_duplicates(
                image_paths,
                exclude=exact_paths,
                progress_callback=_perceptual_progress,
                should_stop=should_stop,
            )
            results.extend(perceptual)

        return results
