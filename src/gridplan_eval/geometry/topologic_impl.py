"""Topologicpy implementation of GeometryEngine.

Wraps existing topologic_utils functionality behind the GeometryEngine interface.

This module requires the 'topologic' extra to be installed:
    pip install gridplan-eval[topologic]
"""

import logging
from typing import Any

try:
    from topologicpy.Topology import Topology
    from topologicpy.Dictionary import Dictionary
    from topologicpy.Edge import Edge
    from topologicpy.Vertex import Vertex
    from topologicpy.Graph import Graph
    TOPOLOGIC_AVAILABLE = True
except ImportError:
    TOPOLOGIC_AVAILABLE = False
    Topology = None
    Dictionary = None
    Edge = None
    Vertex = None
    Graph = None

logger = logging.getLogger(__name__)


def _check_topologic_available():
    """Check if topologicpy is available, raise helpful error if not."""
    if not TOPOLOGIC_AVAILABLE:
        raise ImportError(
            "TopologicGeometry requires topologicpy. "
            "Install with: pip install gridplan-eval[topologic]"
        )


class TopologicGeometry:
    """Topologicpy-based implementation of GeometryEngine."""

    def __init__(self):
        """Initialize TopologicGeometry, checking for topologicpy availability."""
        _check_topologic_available()

    def _get_all_shells(self, shell: Any) -> list:
        """Get all shell fragments from a space topology.

        Args:
            shell: Shell or Cluster topology

        Returns:
            List of Shell objects
        """
        if not shell:
            return []

        topology_dict = Topology.Dictionary(shell)
        is_fragmented = (
            Dictionary.ValueAtKey(topology_dict, "is_fragmented")
            if topology_dict
            else False
        )

        if is_fragmented:
            fragments = Topology.SubTopologies(shell, "Shell")
            return fragments if fragments else []
        else:
            return [shell]

    def get_cell_count(self, shell: Any) -> int:
        """Get number of cells in a space."""
        if not shell:
            return 0

        try:
            shells = self._get_all_shells(shell)
            total = 0
            for s in shells:
                faces = Topology.Faces(s)
                if faces:
                    total += len(faces)
            return total
        except Exception as e:
            logger.error(f"Error counting cells: {e}")
            return 0

    def check_contiguous(self, shell: Any) -> bool:
        """Check if space is contiguous."""
        if not shell:
            return False

        try:
            topology_dict = Topology.Dictionary(shell)
            if topology_dict:
                is_fragmented = Dictionary.ValueAtKey(
                    topology_dict, "is_fragmented")
                if is_fragmented is not None:
                    return not is_fragmented
            # Default to True for legacy shells without metadata
            return True
        except Exception as e:
            logger.error(f"Error checking contiguity: {e}")
            return False

    def check_adjacent(self, shell1: Any, shell2: Any) -> bool:
        """Check if two spaces share at least one edge."""
        if not shell1 or not shell2:
            return False

        try:
            shells1 = self._get_all_shells(shell1)
            shells2 = self._get_all_shells(shell2)

            for s1 in shells1:
                for s2 in shells2:
                    shared_edges = Topology.SharedEdges(s1, s2)
                    if shared_edges and len(shared_edges) > 0:
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking adjacency: {e}")
            return False

    def check_facade_access(self, shell: Any, grid_shell: Any) -> bool:
        """Check if space touches the grid perimeter."""
        if not shell or not grid_shell:
            return False

        try:
            space_edges = Topology.Edges(shell)
            grid_edges = Topology.Edges(grid_shell)

            if not space_edges or not grid_edges:
                return False

            for space_edge in space_edges:
                for grid_edge in grid_edges:
                    if self._edges_coincide(space_edge, grid_edge):
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking facade access: {e}")
            return False

    def _edges_coincide(self, edge1: Any, edge2: Any, tolerance: float = 0.001) -> bool:
        """Check if two edges coincide."""
        try:
            v1_start = Edge.StartVertex(edge1)
            v1_end = Edge.EndVertex(edge1)
            v2_start = Edge.StartVertex(edge2)
            v2_end = Edge.EndVertex(edge2)

            match_forward = (
                Vertex.Distance(v1_start, v2_start) < tolerance
                and Vertex.Distance(v1_end, v2_end) < tolerance
            )
            match_reverse = (
                Vertex.Distance(v1_start, v2_end) < tolerance
                and Vertex.Distance(v1_end, v2_start) < tolerance
            )
            return match_forward or match_reverse
        except Exception:
            return False

    def get_rectangularity(self, shell: Any) -> float:
        """Calculate rectangularity score (0.0 to 1.0)."""
        if not shell:
            return 0.0

        try:
            bbox = Topology.BoundingBox(shell)
            if not bbox:
                return 0.0

            bbox_area = Topology.Area(bbox)
            if bbox_area == 0:
                return 0.0

            space_area = Topology.Area(shell)
            rectangularity = space_area / bbox_area if bbox_area > 0 else 0.0
            return min(rectangularity, 1.0)
        except Exception as e:
            logger.error(f"Error calculating rectangularity: {e}")
            return 0.0

    def has_bottleneck(self, shell: Any) -> bool:
        """Check for 1-cell-wide bottleneck sections using bridge detection."""
        if not shell:
            return False

        try:
            faces = Topology.Faces(shell)
            if not faces or len(faces) <= 2:
                return False

            # Create graph from shell
            graph = Graph.ByTopology(shell, direct=True)
            if not graph:
                return False

            # Get vertices (cells) and edges (adjacencies)
            vertices = Graph.Vertices(graph)
            edges = Graph.Edges(graph)

            if not vertices or not edges:
                return False

            # Check for bridge edges (edges whose removal disconnects graph)
            # A bridge indicates a bottleneck
            for edge in edges:
                # Get edge vertices
                edge_vertices = Topology.Vertices(edge)
                if not edge_vertices or len(edge_vertices) != 2:
                    continue

                # Try removing edge and check connectivity
                remaining_edges = [e for e in edges if e != edge]
                if remaining_edges:
                    test_graph = Graph.ByVerticesEdges(
                        vertices, remaining_edges)
                    if test_graph:
                        components = Graph.ConnectedComponents(test_graph)
                        if components and len(components) > 1:
                            return True  # Found a bridge

            return False
        except Exception as e:
            logger.error(f"Error checking bottleneck: {e}")
            return False

    def cell_in_space(self, shell: Any, row: int, col: int) -> bool:
        """Check if a cell with given coordinates is in the space."""
        if not shell:
            return False

        try:
            target_cell_id = f"{row};{col}"
            shells = self._get_all_shells(shell)

            for s in shells:
                faces = Topology.Faces(s)
                if not faces:
                    continue

                for face in faces:
                    face_dict = Topology.Dictionary(face)
                    if face_dict:
                        cell_id = Dictionary.ValueAtKey(face_dict, "cell_id")
                        if cell_id == target_cell_id:
                            return True
            return False
        except Exception as e:
            logger.warning(f"Error checking cell ({row},{col}) in space: {e}")
            return False

    def find_spaces_by_type(
        self,
        space_shells: dict[str, Any],
        space_type: str,
        space_types: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Find all spaces matching a given type."""
        result = {}
        for space_id, shell in space_shells.items():
            # Use explicit space_types mapping if provided, otherwise infer from ID
            if space_types is not None:
                actual_type = space_types.get(space_id, "")
            else:
                actual_type = self.get_space_type(space_id)

            if actual_type == space_type:
                result[space_id] = shell
        return result

    def get_cell_ids(self, shell: Any) -> list[str]:
        """Get all cell IDs from a space shell."""
        if not shell:
            return []

        try:
            cell_ids = []
            shells = self._get_all_shells(shell)

            for s in shells:
                faces = Topology.Faces(s)
                if not faces:
                    continue

                for face in faces:
                    face_dict = Topology.Dictionary(face)
                    if face_dict:
                        cell_id = Dictionary.ValueAtKey(face_dict, "cell_id")
                        if cell_id:
                            cell_ids.append(cell_id)
            return cell_ids
        except Exception as e:
            logger.error(f"Error getting cell IDs: {e}")
            return []

    def get_invalid_cell_ids(self, shell: Any) -> list[str]:
        """Get cell IDs that were marked as out of bounds."""
        if not shell:
            return []

        try:
            topology_dict = Topology.Dictionary(shell)
            if not topology_dict:
                return []

            invalid_ids = Dictionary.ValueAtKey(
                topology_dict, "invalid_cell_ids")
            return invalid_ids if invalid_ids else []
        except Exception as e:
            logger.error(f"Error getting invalid cell IDs: {e}")
            return []

    def build_connectivity_graph(
        self,
        space_shells: dict[str, Any],
        doors: list[dict[str, str | None]],
    ) -> tuple[bool, int]:
        """Build connectivity graph and check if all spaces are connected."""
        if not space_shells:
            return True, 0

        try:
            # Build adjacency graph based on doors
            # Each space is a node, doors create edges
            from collections import defaultdict

            adjacency = defaultdict(set)
            all_spaces = set(space_shells.keys())

            for door in doors:
                source_id = door["source_space_id"]
                target_id = door["target_space_id"]
                if source_id in all_spaces and target_id in all_spaces:
                    adjacency[source_id].add(target_id)
                    adjacency[target_id].add(source_id)

            # Find connected components using BFS
            visited = set()
            num_components = 0

            for space_id in all_spaces:
                if space_id not in visited:
                    num_components += 1
                    # BFS from this space
                    queue = [space_id]
                    while queue:
                        current = queue.pop(0)
                        if current in visited:
                            continue
                        visited.add(current)
                        for neighbor in adjacency[current]:
                            if neighbor not in visited:
                                queue.append(neighbor)

            is_connected = num_components == 1
            return is_connected, num_components

        except Exception as e:
            logger.error(f"Error building connectivity graph: {e}")
            return False, 0

    def get_space_type(self, space_id: str) -> str:
        """Extract space type from space ID.

        Space IDs follow pattern: {type}_{index} (e.g., "bedroom_1", "kitchen_1")
        """
        if not space_id:
            return ""

        print("Extracting type from space ID:", space_id)

        # Split on last underscore to handle types with underscores
        parts = space_id.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            print("Extracted type:", parts[0])
            return parts[0]
        print("No match found, returning original ID")
        return space_id  # Return as-is if doesn't match pattern
