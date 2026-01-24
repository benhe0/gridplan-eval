"""Grid utilities for constraint evaluation v2.

This module provides grid creation and cell management functionality,
migrated from the legacy constraint_eval.topology_builder module.
"""

from .types import AllocationItem
from .topology import (
    GridTopologyError,
    DictionaryTransferError,
    CellNotFoundError,
    ShellBuildError,
    make_grid,
    build_shell_from_cell_ids,
    get_grid_cell_by_id,
    group_contiguous_faces,
)

__all__ = [
    "AllocationItem",
    "GridTopologyError",
    "DictionaryTransferError",
    "CellNotFoundError",
    "ShellBuildError",
    "make_grid",
    "build_shell_from_cell_ids",
    "get_grid_cell_by_id",
    "group_contiguous_faces",
]
