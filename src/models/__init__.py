"""Mô hình dữ liệu và chuyển đổi kết quả."""

from .duplicate_groups import DuplicateGroupManager
from .serializers import (
    duplicate_group_to_row,
    duplicate_groups_to_rows,
    invalid_result_to_row,
    invalid_results_to_rows,
)

__all__ = [
    "DuplicateGroupManager",
    "duplicate_group_to_row",
    "duplicate_groups_to_rows",
    "invalid_result_to_row",
    "invalid_results_to_rows",
]
