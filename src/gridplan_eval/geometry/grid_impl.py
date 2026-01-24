"""Pure Python + networkx implementation of GeometryEngine.

Uses discrete (row, col) cell coordinates for grid-based spatial operations.
For a grid-based system, this is more efficient than full topological computation.

- Adjacency: cells are adjacent if |row1-row2| + |col1-col2| == 1 (4-connectivity)
- Area: cell_count (number of cells in space)
- Contiguity: BFS/DFS on cell adjacency
- Bottleneck: networkx articulation_points()
- Facade access: any cell on grid boundary (row 0, row max, col 0, col max)
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GridSpace:
    """Represents a space as a set of grid cells.

    Attributes:
        cells: Immutable set of (row, col) coordinate tuples
        metadata: Optional metadata dict (is_fragmented, invalid_cell_ids, etc.)
    """

    cells: frozenset[tuple[int, int]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure metadata is a dict (needed because frozen=True prevents assignment)
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class GridGeometry:
    """Pure Python + networkx implementation of GeometryEngine.

    Uses 4-connectivity (von Neumann neighborhood) for adjacency:
    two cells are adjacent if they share an edge (not diagonal).
    """

    def __init__(self, grid_rows: int, grid_cols: int):
        """Initialize with grid dimensions.

        Args:
            grid_rows: Number of rows in the grid
            grid_cols: Number of columns in the grid
        """
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

    def _get_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Get 4-connected neighbors of a cell.

        Args:
            row: Row coordinate
            col: Column coordinate

        Returns:
            List of valid neighbor (row, col) tuples
        """
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.grid_rows and 0 <= nc < self.grid_cols:
                neighbors.append((nr, nc))
        return neighbors

    def _is_on_boundary(self, row: int, col: int) -> bool:
        """Check if cell is on grid boundary.

        Args:
            row: Row coordinate
            col: Column coordinate

        Returns:
            True if cell is on any edge of the grid
        """
        return (
            row == 0
            or row == self.grid_rows - 1
            or col == 0
            or col == self.grid_cols - 1
        )

    def _build_cell_graph(self, cells: frozenset[tuple[int, int]]) -> nx.Graph:
        """Build networkx graph from cell set.

        Nodes are cells, edges connect 4-adjacent cells.

        Args:
            cells: Set of (row, col) coordinates

        Returns:
            networkx Graph with cells as nodes
        """
        graph = nx.Graph()
        graph.add_nodes_from(cells)

        for cell in cells:
            row, col = cell
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (row + dr, col + dc)
                if neighbor in cells:
                    graph.add_edge(cell, neighbor)

        return graph

    def get_cell_count(self, shell: Any) -> int:
        """Get number of cells in a space.

        Args:
            shell: GridSpace representing the space

        Returns:
            Number of cells in the space
        """
        if shell is None:
            return 0
        if not isinstance(shell, GridSpace):
            return 0
        return len(shell.cells)

    def check_contiguous(self, shell: Any) -> bool:
        """Check if space is contiguous (single connected region).

        Uses BFS to check if all cells are reachable from any starting cell.

        Args:
            shell: GridSpace representing the space

        Returns:
            True if space is a single contiguous region
        """
        if shell is None:
            return False
        if not isinstance(shell, GridSpace):
            return False

        # Check metadata first
        if shell.metadata.get("is_fragmented"):
            return False

        cells = shell.cells
        if len(cells) == 0:
            return True  # Empty space is vacuously contiguous
        if len(cells) == 1:
            return True

        # BFS from first cell
        start = next(iter(cells))
        visited = {start}
        queue = deque([start])

        while queue:
            row, col = queue.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (row + dr, col + dc)
                if neighbor in cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == len(cells)

    def check_adjacent(self, shell1: Any, shell2: Any) -> bool:
        """Check if two spaces share at least one edge.

        Spaces are adjacent if any cell from shell1 is 4-adjacent
        to any cell from shell2.

        Args:
            shell1: First space (GridSpace)
            shell2: Second space (GridSpace)

        Returns:
            True if spaces share at least one edge
        """
        if shell1 is None or shell2 is None:
            return False
        if not isinstance(shell1, GridSpace) or not isinstance(shell2, GridSpace):
            return False

        cells1 = shell1.cells
        cells2 = shell2.cells

        for row, col in cells1:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (row + dr, col + dc)
                if neighbor in cells2:
                    return True

        return False

    def check_facade_access(self, shell: Any, grid_shell: Any) -> bool:
        """Check if space touches the grid perimeter.

        A space has facade access if any of its cells is on the grid boundary.

        Args:
            shell: Space to check (GridSpace)
            grid_shell: Not used in grid implementation (kept for API compatibility)

        Returns:
            True if space touches grid perimeter
        """
        if shell is None:
            return False
        if not isinstance(shell, GridSpace):
            return False

        for row, col in shell.cells:
            if self._is_on_boundary(row, col):
                return True

        return False

    def get_rectangularity(self, shell: Any) -> float:
        """Calculate rectangularity score (0.0 to 1.0).

        Rectangularity = actual_cells / bounding_box_cells

        Args:
            shell: GridSpace representing the space

        Returns:
            Rectangularity score (1.0 = perfect rectangle)
        """
        if shell is None:
            return 0.0
        if not isinstance(shell, GridSpace):
            return 0.0

        cells = shell.cells
        if len(cells) == 0:
            return 0.0

        # Calculate bounding box
        rows = [r for r, c in cells]
        cols = [c for r, c in cells]

        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)

        bbox_height = max_row - min_row + 1
        bbox_width = max_col - min_col + 1
        bbox_area = bbox_height * bbox_width

        if bbox_area == 0:
            return 0.0

        return len(cells) / bbox_area

    def has_bottleneck(self, shell: Any) -> bool:
        """Check for 1-cell-wide sections using articulation point detection.

        A bottleneck is a single cell whose removal would disconnect
        parts of the space (an articulation point in graph terms).

        Args:
            shell: GridSpace representing the space

        Returns:
            True if space has bottleneck cells
        """
        if shell is None:
            return False
        if not isinstance(shell, GridSpace):
            return False

        cells = shell.cells
        if len(cells) <= 2:
            return False  # No bottleneck possible with 0, 1, or 2 cells

        graph = self._build_cell_graph(cells)
        articulation_points = list(nx.articulation_points(graph))

        return len(articulation_points) > 0

    def cell_in_space(self, shell: Any, row: int, col: int) -> bool:
        """Check if a cell with given coordinates is in the space.

        Args:
            shell: GridSpace representing the space
            row: Row coordinate of the cell
            col: Column coordinate of the cell

        Returns:
            True if cell is part of the space
        """
        if shell is None:
            return False
        if not isinstance(shell, GridSpace):
            return False

        return (row, col) in shell.cells

    def find_spaces_by_type(
        self,
        space_shells: dict[str, Any],
        space_type: str,
        space_types: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Find all spaces matching a given type.

        Args:
            space_shells: Dictionary mapping space_id to GridSpace
            space_type: Type to filter by (e.g., "bedroom")
            space_types: Optional mapping of space_id to type

        Returns:
            Dictionary of matching space_id -> GridSpace pairs
        """
        result = {}
        for space_id, shell in space_shells.items():
            if space_types is not None:
                actual_type = space_types.get(space_id, "")
            else:
                actual_type = self.get_space_type(space_id)

            if actual_type == space_type:
                result[space_id] = shell

        return result

    def get_cell_ids(self, shell: Any) -> list[str]:
        """Get all cell IDs from a space.

        Cell IDs are in format "row;col".

        Args:
            shell: GridSpace representing the space

        Returns:
            List of cell ID strings
        """
        if shell is None:
            return []
        if not isinstance(shell, GridSpace):
            return []

        return [f"{row};{col}" for row, col in shell.cells]

    def get_invalid_cell_ids(self, shell: Any) -> list[str]:
        """Get cell IDs that were marked as out of bounds.

        Reads from shell metadata set during space building.

        Args:
            shell: GridSpace representing the space

        Returns:
            List of invalid cell ID strings
        """
        if shell is None:
            return []
        if not isinstance(shell, GridSpace):
            return []

        return shell.metadata.get("invalid_cell_ids", [])

    def build_connectivity_graph(
        self,
        space_shells: dict[str, Any],
        doors: list[dict[str, str | None]],
    ) -> tuple[bool, int]:
        """Build connectivity graph and check if all spaces are connected.

        Spaces are nodes, doors create edges between them.

        Args:
            space_shells: Dictionary mapping space_id to GridSpace
            doors: List of door dicts with source_space_id, target_space_id

        Returns:
            Tuple of (is_connected, num_components)
        """
        if not space_shells:
            return True, 0

        graph = nx.Graph()
        graph.add_nodes_from(space_shells.keys())

        for door in doors:
            source_id = door.get("source_space_id")
            target_id = door.get("target_space_id")
            if source_id in space_shells and target_id in space_shells:
                graph.add_edge(source_id, target_id)

        num_components = nx.number_connected_components(graph)
        is_connected = num_components == 1

        return is_connected, num_components

    def get_space_type(self, space_id: str) -> str:
        """Extract space type from space ID.

        Space IDs follow pattern: {type}_{index} (e.g., "bedroom_1", "kitchen_1")

        Args:
            space_id: Full space ID

        Returns:
            Space type (e.g., "bedroom")
        """
        if not space_id:
            return ""

        parts = space_id.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]

        return space_id
