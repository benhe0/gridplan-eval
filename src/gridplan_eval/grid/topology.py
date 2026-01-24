"""
Grid Topology Builder for Constraint Evaluation v2

This module provides functionality to create grid-based topologies with spaces
for constraint evaluation. Migrated from legacy constraint_eval.topology_builder.

Includes utilities for:
- Creating grid structures
- Managing cell dictionaries
- Building shells from cell IDs

This module requires the 'topologic' extra to be installed:
    pip install gridplan-eval[topologic]
"""

import logging
import random
from typing import List, Dict, Optional, Any

try:
    from topologicpy.Topology import Topology
    from topologicpy.Dictionary import Dictionary
    from topologicpy.Shell import Shell
    from topologicpy.Face import Face
    from topologicpy.Edge import Edge
    from topologicpy.Vertex import Vertex
    from topologicpy.Cluster import Cluster
    TOPOLOGIC_AVAILABLE = True
except ImportError:
    TOPOLOGIC_AVAILABLE = False
    Topology = None
    Dictionary = None
    Shell = None
    Face = None
    Edge = None
    Vertex = None
    Cluster = None

from .types import AllocationItem

logger = logging.getLogger(__name__)


def _check_topologic_available():
    """Check if topologicpy is available, raise helpful error if not."""
    if not TOPOLOGIC_AVAILABLE:
        raise ImportError(
            "Grid topology module requires topologicpy. "
            "Install with: pip install gridplan-eval[topologic]"
        )


# Custom Exceptions
class GridTopologyError(Exception):
    """Base exception for grid topology operations."""

    pass


class DictionaryTransferError(GridTopologyError):
    """Raised when dictionary transfer fails."""

    pass


class CellNotFoundError(GridTopologyError):
    """Raised when a grid cell cannot be found."""

    pass


class ShellBuildError(GridTopologyError):
    """Raised when shell building fails."""

    pass


# Utility Functions
def random_color() -> str:
    """
    Generate a random hex color code.

    Returns:
        str: A hex color code in format "#RRGGBB"
    """
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


def transfer_dicts(
    source_topologies: List[Any],
    target_topology: Any,
    source_topology_type: str,
    target_topology_type: str,
) -> Any:
    """
    Transfer dictionaries from source topologies to a target topology.

    Supported transfers:
    - Face -> Shell: Transfer dictionaries from faces to a shell using selectors
    - Shell -> Face: Transfer dictionaries from shells to faces (1-to-1 mapping)

    Args:
        source_topologies: List of source topologies (e.g., Faces or Shells)
        target_topology: The target topology (e.g., Shell or list of Faces)
        source_topology_type: Type of the source topology ("Face" or "Shell")
        target_topology_type: Type of the target topology ("Shell" or "Face")

    Returns:
        The target topology with transferred dictionaries

    Raises:
        DictionaryTransferError: If dictionary transfer fails
        ValueError: If topology types are not supported or target is invalid
    """
    _check_topologic_available()
    logger.debug(
        f"Transferring dictionaries from {source_topology_type} to {target_topology_type}"
    )

    try:
        if source_topology_type == "Face" and target_topology_type == "Shell":
            logger.debug(f"Found {len(source_topologies)} source faces")

            faces = source_topologies
            selectors = []

            for face in faces:
                try:
                    face_dict = Topology.Dictionary(face)
                    if face_dict:
                        internal_vertex = Topology.Centroid(face)
                        if internal_vertex:
                            face = Topology.SetDictionary(
                                internal_vertex, face_dict)
                            selectors.append(internal_vertex)
                except Exception as e:
                    logger.warning(f"Failed to process face dictionary: {e}")
                    continue

            if selectors:
                try:
                    target_topology = Topology.TransferDictionariesBySelectors(
                        target_topology, selectors, tranFaces=True, tranVertices=True
                    )
                    logger.debug("Dictionaries transferred to target shell")
                except Exception as e:
                    raise DictionaryTransferError(
                        f"Failed to transfer dictionaries using selectors: {e}"
                    ) from e
            else:
                logger.warning("No selectors found for source topology")

            return target_topology

        elif source_topology_type == "Shell" and target_topology_type == "Face":
            logger.debug(f"Found {len(source_topologies)} source shells")

            # target_topology should be a list of faces
            if not isinstance(target_topology, list):
                raise ValueError(
                    "Target topology must be a list of faces for Shell->Face transfer"
                )

            if len(source_topologies) != len(target_topology):
                raise ValueError(
                    f"Mismatch between source shells ({len(source_topologies)}) "
                    f"and target faces ({len(target_topology)})"
                )

            # Transfer dictionaries from each shell to corresponding face
            updated_faces = []
            for shell, face in zip(source_topologies, target_topology):
                try:
                    shell_dict = Topology.Dictionary(shell)
                    if shell_dict:
                        face = Topology.SetDictionary(face, shell_dict)
                        logger.debug(
                            "Dictionary transferred from shell to face")
                        updated_faces.append(face)
                    else:
                        logger.warning("No dictionary found on shell")
                        updated_faces.append(face)
                except Exception as e:
                    logger.warning(
                        f"Failed to transfer dictionary from shell to face: {e}"
                    )
                    updated_faces.append(face)
                    continue

            logger.debug("Dictionaries transferred from shells to faces")
            return updated_faces

        else:
            raise ValueError(
                f"Unsupported topology types: {source_topology_type} -> {target_topology_type}"
            )
    except Exception as e:
        if isinstance(e, (DictionaryTransferError, ValueError)):
            raise
        raise DictionaryTransferError(
            f"Dictionary transfer failed: {e}") from e


def make_grid(rows: int, cols: int, cell_size: float) -> Shell:
    """
    Create a grid of faces with dictionary metadata.

    Args:
        rows: Number of rows in the grid
        cols: Number of columns in the grid
        cell_size: Size of each cell

    Returns:
        Shell: A shell containing all grid faces with metadata

    Raises:
        GridTopologyError: If grid creation fails
        ValueError: If rows, cols, or cell_size are invalid
    """
    _check_topologic_available()
    if rows <= 0 or cols <= 0:
        raise ValueError(
            f"Rows and columns must be positive: rows={rows}, cols={cols}")
    if cell_size <= 0:
        raise ValueError(f"Cell size must be positive: {cell_size}")

    try:
        faces = []

        for i in range(rows):
            for j in range(cols):
                try:
                    v1 = Vertex.ByCoordinates(j * cell_size, i * cell_size, 0)
                    v2 = Vertex.ByCoordinates(
                        (j + 1) * cell_size, i * cell_size, 0)
                    v3 = Vertex.ByCoordinates(
                        (j + 1) * cell_size, (i + 1) * cell_size, 0
                    )
                    v4 = Vertex.ByCoordinates(
                        j * cell_size, (i + 1) * cell_size, 0)

                    face = Face.ByVertices([v1, v2, v3, v4])

                    dictionary = Topology.Dictionary(face)
                    dictionary = Dictionary.SetValueAtKey(
                        dictionary, "row", str(i))
                    dictionary = Dictionary.SetValueAtKey(
                        dictionary, "col", str(j))
                    dictionary = Dictionary.SetValueAtKey(
                        dictionary, "cell_id", f"{i};{j}"
                    )

                    face = Topology.SetDictionary(face, dictionary)
                    faces.append(face)
                except Exception as e:
                    raise GridTopologyError(
                        f"Failed to create face at position ({i}, {j}): {e}"
                    ) from e

        shell = Shell.ByFaces(faces)
        if not shell:
            raise GridTopologyError("Failed to create shell from faces")

        shell = transfer_dicts(faces, shell, "Face", "Shell")
        logger.debug(
            f"Created grid shell: {rows}x{cols} with {len(faces)} cells")

        return shell
    except Exception as e:
        if isinstance(e, (GridTopologyError, ValueError)):
            raise
        raise GridTopologyError(f"Grid creation failed: {e}") from e


def group_contiguous_faces(faces: List[Face]) -> List[List[Face]]:
    """
    Group faces into contiguous fragments using connectivity analysis.

    Faces are considered contiguous if they share at least one edge.
    Uses BFS to find connected components.

    Args:
        faces: List of faces to group

    Returns:
        List of face groups, where each group forms a contiguous region

    Example:
        >>> faces = [face_00, face_01, face_33, face_34]  # Two 2-cell regions
        >>> fragments = group_contiguous_faces(faces)
        >>> len(fragments)  # 2 separate fragments
        2
    """
    _check_topologic_available()
    if not faces:
        return []

    if len(faces) == 1:
        return [faces]

    # Use id() to track visited faces (object identity)
    visited = set()
    fragments = []

    for start_face in faces:
        face_id = id(start_face)
        if face_id in visited:
            continue

        # BFS to find all connected faces
        fragment = []
        queue = [start_face]
        visited.add(face_id)

        while queue:
            current = queue.pop(0)
            fragment.append(current)

            # Check adjacency with unvisited faces
            for other_face in faces:
                other_id = id(other_face)
                if other_id not in visited:
                    try:
                        shared_edges = Topology.SharedEdges(
                            current, other_face)
                        if shared_edges and len(shared_edges) > 0:
                            visited.add(other_id)
                            queue.append(other_face)
                    except Exception as e:
                        logger.debug(f"Error checking edge sharing: {e}")
                        continue

        if fragment:
            fragments.append(fragment)

    logger.debug(
        f"Grouped {len(faces)} faces into {len(fragments)} fragment(s)")
    return fragments


def get_grid_cell_by_id(shell: Shell, id_key: str, id_value: str) -> Optional[Face]:
    """
    Get a grid cell by its ID.

    Args:
        shell: The shell containing the grid
        id_key: The dictionary key to search by
        id_value: The value to match

    Returns:
        The matching face, or None if not found

    Raises:
        CellNotFoundError: If the shell is invalid
    """
    _check_topologic_available()
    if not shell:
        raise CellNotFoundError("Shell is None or invalid")

    try:
        faces = Topology.Faces(shell)
        filtered = Topology.Filter(
            faces, "Face", searchType="equal to", key=id_key, value=id_value
        )
        logger.debug(
            f"Filtered cells for {id_key}={id_value}: {len(filtered.get('filtered', []))} found"
        )

        if filtered and "filtered" in filtered and filtered["filtered"]:
            return filtered["filtered"][0]
        return None
    except Exception as e:
        raise CellNotFoundError(
            f"Failed to get cell by ID {id_key}={id_value}: {e}"
        ) from e


def build_shell_from_cell_ids(
    space: AllocationItem, grid: Shell, allow_fragments: bool = True
) -> Optional[Any]:
    """
    Build a shell (or cluster of shells) from a list of cell IDs.

    Handles non-contiguous spaces by creating separate shells for each
    contiguous fragment and combining them into a Cluster. This allows
    evaluation to continue even when spaces are fragmented.

    Args:
        space: AllocationItem containing cell IDs
        grid: The grid shell to extract cells from
        allow_fragments: If True, create Cluster for non-contiguous cells.
                        If False, return None for non-contiguous spaces.

    Returns:
        - Shell if space is contiguous (single fragment)
        - Cluster of Shells if space is fragmented (multiple fragments)
        - None if no valid cells found

    Metadata added to result:
        - is_fragmented: bool - True if space has multiple fragments
        - fragment_count: int - Number of contiguous fragments
        - invalid_cell_ids: list - Cell IDs that were out of bounds
        - (for Clusters) Each shell also has fragment_index

    Raises:
        ValueError: If space has no cell IDs

    Note:
        Does NOT raise ShellBuildError for non-contiguous spaces when
        allow_fragments=True. This ensures evaluation continues even
        with topology issues.
    """
    _check_topologic_available()
    if not space.cell_ids:
        raise ValueError(f"Space {space.name} has no cell IDs")

    try:
        # Collect valid cells and track invalid cell IDs
        cells = []
        invalid_cell_ids = []

        for cell_id in space.cell_ids:
            try:
                cell = get_grid_cell_by_id(grid, "cell_id", cell_id)
                if cell:
                    cells.append(cell)
                else:
                    logger.warning(
                        f"Cell {cell_id} not found in grid for space {space.name}"
                    )
                    invalid_cell_ids.append(cell_id)
            except CellNotFoundError as e:
                logger.warning(f"{e}")
                invalid_cell_ids.append(cell_id)
                continue

        if not cells:
            logger.warning(f"No valid cells found for space {space.name}")
            return None

        if invalid_cell_ids:
            logger.info(
                f"Space {space.name}: {len(cells)} valid cells, {len(invalid_cell_ids)} invalid cell IDs"
            )

        # Group cells into contiguous fragments
        fragments = group_contiguous_faces(cells)

        if len(fragments) == 1:
            # Contiguous space - standard single shell
            shell = Shell.ByFaces(fragments[0])
            if not shell:
                logger.error(
                    f"Failed to create shell for contiguous space {space.name} "
                    f"with {len(cells)} cells"
                )
                return None

            # Add metadata indicating this is NOT fragmented
            shell_dict = Topology.Dictionary(
                shell) or Dictionary.ByKeysValues([], [])
            shell_dict = Dictionary.SetValueAtKey(
                shell_dict, "is_fragmented", False)
            shell_dict = Dictionary.SetValueAtKey(
                shell_dict, "fragment_count", 1)
            shell_dict = Dictionary.SetValueAtKey(
                shell_dict, "invalid_cell_ids", invalid_cell_ids
            )
            shell = Topology.SetDictionary(shell, shell_dict)

            logger.debug(
                f"Created contiguous shell for {space.name} with {len(cells)} cells"
            )
            return shell

        else:
            # Non-contiguous space - multiple fragments
            if not allow_fragments:
                logger.error(
                    f"Space {space.name} is non-contiguous ({len(fragments)} fragments) "
                    f"and fragmentation is not allowed"
                )
                return None

            logger.debug(
                f"Space {space.name} is FRAGMENTED into {len(fragments)} parts. "
                f"Fragment sizes: {[len(f) for f in fragments]} cells"
            )

            # Create shell for each fragment
            fragment_shells = []
            for i, fragment_faces in enumerate(fragments):
                frag_shell = Shell.ByFaces(fragment_faces)
                if frag_shell:
                    # Add fragment-specific metadata
                    frag_dict = Topology.Dictionary(
                        frag_shell
                    ) or Dictionary.ByKeysValues([], [])
                    frag_dict = Dictionary.SetValueAtKey(
                        frag_dict, "fragment_index", i)
                    frag_dict = Dictionary.SetValueAtKey(
                        frag_dict, "fragment_size", len(fragment_faces)
                    )
                    frag_shell = Topology.SetDictionary(frag_shell, frag_dict)
                    fragment_shells.append(frag_shell)
                else:
                    logger.warning(
                        f"Failed to create shell for fragment {i} of space {space.name}"
                    )

            if not fragment_shells:
                logger.error(
                    f"No valid fragment shells created for space {space.name}")
                return None

            # Combine fragments into a Cluster
            cluster = Cluster.ByTopologies(fragment_shells)
            if not cluster:
                logger.error(
                    f"Failed to create cluster for fragmented space {space.name}"
                )
                return None

            # Add overall metadata to cluster
            cluster_dict = Topology.Dictionary(cluster) or Dictionary.ByKeysValues(
                [], []
            )
            cluster_dict = Dictionary.SetValueAtKey(
                cluster_dict, "is_fragmented", True
            )
            cluster_dict = Dictionary.SetValueAtKey(
                cluster_dict, "fragment_count", len(fragments)
            )
            cluster_dict = Dictionary.SetValueAtKey(
                cluster_dict, "invalid_cell_ids", invalid_cell_ids
            )
            cluster = Topology.SetDictionary(cluster, cluster_dict)

            logger.debug(
                f"Created fragmented topology for {space.name}: "
                f"{len(fragment_shells)} fragments, {len(cells)} total cells"
            )
            return cluster

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        logger.error(
            f"Unexpected error building shell for space {space.name}: {e}")
        return None
