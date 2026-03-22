"""Constraint implementations.

All 13 constraint types for floor plan evaluation.
"""

from ..constraints.base import Constraint
from ..constraints.logging_config import (
    configure_constraint_logging,
    is_debug_enabled,
)

# Space constraints
from ..constraints.presence import PresenceConstraint
from ..constraints.area import AreaConstraint
from ..constraints.contiguity import ContiguityConstraint
from ..constraints.shape import ShapeConstraint
from ..constraints.facade import FacadeConstraint
from ..constraints.min_width import MinWidthConstraint

# Connectivity constraints
from ..constraints.adjacency import AdjacencyConstraint
from ..constraints.door import DoorConstraint
from ..constraints.avoidance import AvoidanceConstraint
from ..constraints.global_connectivity import GlobalConnectivityConstraint

# Layout constraints
from ..constraints.grid_bounds import GridBoundsConstraint
from ..constraints.cell_overlap import CellOverlapConstraint
from ..constraints.allocation import AllocationConstraint
from ..constraints.window_placement import WindowPlacementConstraint

__all__ = [
    "Constraint",
    "configure_constraint_logging",
    "is_debug_enabled",
    # Space
    "PresenceConstraint",
    "AreaConstraint",
    "ContiguityConstraint",
    "ShapeConstraint",
    "FacadeConstraint",
    "MinWidthConstraint",
    # Connectivity
    "AdjacencyConstraint",
    "DoorConstraint",
    "AvoidanceConstraint",
    "GlobalConnectivityConstraint",
    # Layout
    "GridBoundsConstraint",
    "CellOverlapConstraint",
    "AllocationConstraint",
    "WindowPlacementConstraint",
]
