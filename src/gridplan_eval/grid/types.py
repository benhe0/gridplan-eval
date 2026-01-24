"""Type definitions for grid operations.

Migrated from mytypes.py for self-contained v2 package.
"""

from pydantic import BaseModel
from typing import List


class AllocationItem(BaseModel):
    """Represents a space allocation with cell assignments.

    Attributes:
        name: Human-readable name of the space
        type: Type or category of the space (e.g., "bedroom", "bathroom")
        cell_ids: List of grid cell IDs that belong to this space
    """

    name: str
    type: str
    cell_ids: List[str]
