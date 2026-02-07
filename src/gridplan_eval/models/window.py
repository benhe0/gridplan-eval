"""Window data model for grid cell edges."""

from dataclasses import dataclass
from typing import Literal

VALID_EDGES = frozenset({"top", "right", "bottom", "left"})


@dataclass(frozen=True)
class Window:
    """A window on a specific edge of a grid cell.

    Unlike doors (which connect two spaces), a window sits on a single
    cell edge facing the building exterior.

    Edges use geometric directions (top/right/bottom/left), not compass
    directions. Compass mapping is handled separately via orientation config.
    """

    cell_id: str  # "row;col" format
    edge: Literal["top", "right", "bottom", "left"]  # grid-relative direction
    space_id: str | None = None  # resolved from allocation
