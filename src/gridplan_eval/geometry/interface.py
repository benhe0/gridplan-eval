"""Geometry engine interface for spatial operations.

Abstracts topologicpy operations behind a clean protocol to enable
future replacement with alternative geometry libraries.
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class GeometryEngine(Protocol):
    """Abstract interface for geometry operations on floor plan shells.

    All methods accept Shell or Cluster topologies from topologicpy.
    Implementations must handle both contiguous shells and fragmented
    spaces (Clusters with is_fragmented metadata).
    """

    def get_cell_count(self, shell: Any) -> int:
        """Get number of cells in a space.

        Args:
            shell: Shell or Cluster representing the space

        Returns:
            Number of cells (faces) in the space
        """
        ...

    def check_contiguous(self, shell: Any) -> bool:
        """Check if space is contiguous (single connected region).

        Args:
            shell: Shell or Cluster representing the space

        Returns:
            True if space is a single contiguous region
        """
        ...

    def check_adjacent(self, shell1: Any, shell2: Any) -> bool:
        """Check if two spaces share at least one edge.

        Args:
            shell1: First space shell
            shell2: Second space shell

        Returns:
            True if spaces share at least one edge
        """
        ...

    def check_facade_access(self, shell: Any, grid_shell: Any) -> bool:
        """Check if space touches the grid perimeter.

        Args:
            shell: Space shell to check
            grid_shell: Shell representing the entire grid

        Returns:
            True if space touches grid perimeter
        """
        ...

    def get_rectangularity(self, shell: Any) -> float:
        """Calculate rectangularity score (0.0 to 1.0).

        Args:
            shell: Shell representing the space

        Returns:
            Rectangularity score (1.0 = perfect rectangle)
        """
        ...

    def has_bottleneck(self, shell: Any) -> bool:
        """Check for 1-cell-wide sections using bridge detection.

        A bottleneck is a single cell whose removal would disconnect
        parts of the space.

        Args:
            shell: Shell representing the space

        Returns:
            True if space has bottleneck cells
        """
        ...

    def cell_in_space(self, shell: Any, row: int, col: int) -> bool:
        """Check if a cell with given coordinates is in the space.

        Args:
            shell: Shell representing the space
            row: Row coordinate of the cell
            col: Column coordinate of the cell

        Returns:
            True if cell is part of the space
        """
        ...

    def find_spaces_by_type(
        self,
        space_shells: dict[str, Any],
        space_type: str,
        space_types: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Find all spaces matching a given type.

        Args:
            space_shells: Dictionary mapping space_id to Shell
            space_type: Type to filter by (e.g., "bedroom")
            space_types: Optional mapping of space_id to type. If provided,
                uses this for type lookup. Otherwise falls back to inferring
                type from space_id naming convention "{type}_{index}".

        Returns:
            Dictionary of matching space_id -> Shell pairs
        """
        ...

    def get_cell_ids(self, shell: Any) -> list[str]:
        """Get all cell IDs from a space shell.

        Cell IDs are in format "row;col".

        Args:
            shell: Shell representing the space

        Returns:
            List of cell ID strings
        """
        ...

    def get_invalid_cell_ids(self, shell: Any) -> list[str]:
        """Get cell IDs that were marked as out of bounds.

        Reads from shell metadata set during topology building.

        Args:
            shell: Shell representing the space

        Returns:
            List of invalid cell ID strings
        """
        ...

    def build_connectivity_graph(
        self,
        space_shells: dict[str, Any],
        doors: list[tuple[str, str]],
    ) -> tuple[bool, int]:
        """Build connectivity graph and check if all spaces are connected.

        Args:
            space_shells: Dictionary mapping space_id to Shell
            doors: List of (source_id, target_id) door connections

        Returns:
            Tuple of (is_connected, num_components)
        """
        ...

    def get_space_type(self, space_id: str) -> str:
        """Extract space type from space ID.

        Args:
            space_id: Full space ID (e.g., "bedroom_1")

        Returns:
            Space type (e.g., "bedroom")
        """
        ...
