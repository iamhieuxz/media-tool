"""Quản lý danh sách nhóm file trùng lặp dạng dict."""

from __future__ import annotations

from pathlib import Path


class DuplicateGroupManager:
    """Cập nhật duplicate_rows sau khi xoá file."""

    @staticmethod
    def _existing_paths(paths: list[Path]) -> list[Path]:
        """Chỉ giữ các đường dẫn file còn tồn tại trên đĩa."""

        return [path for path in paths if path.exists() and path.is_file()]

    @staticmethod
    def _build_group(group: dict[str, object], paths: list[Path]) -> dict[str, object]:
        kept_str = [str(path) for path in paths]
        sims = group.get("path_similarities", {})
        if isinstance(sims, dict):
            filtered_sims = {k: v for k, v in sims.items() if k in kept_str}
        else:
            filtered_sims = {}
        return {
            "size": group["size"],
            "hash_value": group["hash_value"],
            "paths": kept_str,
            "match_type": group.get("match_type", "exact"),
            "similarity": group.get("similarity", 100.0),
            "path_similarities": filtered_sims,
        }

    @staticmethod
    def prune_missing(groups: list[dict[str, object]]) -> list[dict[str, object]]:
        """Loại file không còn trên đĩa và nhóm chỉ còn 1 file."""

        refreshed: list[dict[str, object]] = []
        for group in groups:
            paths = [Path(item) for item in group.get("paths", []) if isinstance(item, str)]
            existing = DuplicateGroupManager._existing_paths(paths)
            if len(existing) > 1:
                refreshed.append(DuplicateGroupManager._build_group(group, existing))
        return refreshed

    @staticmethod
    def remove_path(
        groups: list[dict[str, object]],
        deleted_path: Path,
    ) -> list[dict[str, object]]:
        """Loại một đường dẫn khỏi các nhóm, giữ nhóm còn >= 2 file."""

        deleted_resolved = deleted_path.resolve()
        return DuplicateGroupManager.remove_paths(groups, {deleted_resolved})

    @staticmethod
    def remove_paths(
        groups: list[dict[str, object]],
        deleted_paths: set[Path],
    ) -> list[dict[str, object]]:
        """Loại nhiều đường dẫn khỏi các nhóm, giữ nhóm còn >= 2 file."""

        resolved_deleted = {path.resolve() for path in deleted_paths}
        refreshed: list[dict[str, object]] = []
        for group in groups:
            paths = [Path(item) for item in group.get("paths", []) if isinstance(item, str)]
            kept_paths = [
                path
                for path in paths
                if path.resolve() not in resolved_deleted and path.exists() and path.is_file()
            ]
            if len(kept_paths) > 1:
                refreshed.append(DuplicateGroupManager._build_group(group, kept_paths))
        return refreshed

    @staticmethod
    def count_deletable(groups: list[dict[str, object]]) -> int:
        """Đếm số file sao chép có thể xoá (giữ file đầu tiên mỗi nhóm)."""

        return sum(max(len(group.get("paths", [])) - 1, 0) for group in groups)
