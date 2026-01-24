"""Connectivity graph builder using topologicpy apertures.

Builds a topologicpy Graph from space shells and door connections
using apertures on shared edges.

This module requires the 'topologic' extra to be installed:
    pip install gridplan-eval[topologic]
"""

import logging
from typing import Any

try:
    from topologicpy.Topology import Topology
    from topologicpy.Dictionary import Dictionary
    from topologicpy.Graph import Graph
    from topologicpy.Face import Face
    from topologicpy.Shell import Shell
    from topologicpy.Vertex import Vertex
    from topologicpy.Edge import Edge
    TOPOLOGIC_AVAILABLE = True
except ImportError:
    TOPOLOGIC_AVAILABLE = False
    Topology = None
    Dictionary = None
    Graph = None
    Face = None
    Shell = None
    Vertex = None
    Edge = None

logger = logging.getLogger(__name__)


def _check_topologic_available():
    """Check if topologicpy is available, raise helpful error if not."""
    if not TOPOLOGIC_AVAILABLE:
        raise ImportError(
            "graph_builder module requires topologicpy. "
            "Install with: pip install gridplan-eval[topologic]"
        )


def _log_topology_info(topology: Any, label: str) -> None:
    """Log detailed topology information for debugging."""
    _check_topologic_available()
    if topology is None:
        logger.debug(f"  {label}: None")
        return

    try:
        topo_type = Topology.TypeAsString(topology)
        logger.debug(f"  {label}: type={topo_type}")

        vertices = Topology.Vertices(topology)
        if vertices:
            logger.debug(f"    vertices: {len(vertices)}")
            for i, v in enumerate(vertices[:4]):
                coords = Vertex.Coordinates(v)
                logger.debug(
                    f"      [{i}] ({coords[0]:.2f}, {coords[1]:.2f}, {coords[2]:.2f})")
            if len(vertices) > 4:
                logger.debug(f"      ... and {len(vertices) - 4} more")

        edges = Topology.Edges(topology)
        if edges:
            logger.debug(f"    edges: {len(edges)}")

        faces = Topology.Faces(topology)
        if faces:
            logger.debug(f"    faces: {len(faces)}")

        topo_dict = Topology.Dictionary(topology)
        if topo_dict:
            keys = Dictionary.Keys(topo_dict)
            if keys:
                logger.debug(f"    dictionary keys: {keys}")
                for key in keys[:5]:
                    value = Dictionary.ValueAtKey(topo_dict, key)
                    logger.debug(f"      {key}: {value}")
    except Exception as e:
        logger.debug(f"  {label}: error getting info - {e}")


def _build_fallback_graph(
    space_shells: dict[str, Any],
    doors: list[dict[str, str | None]],
) -> Any | None:
    """Build connectivity graph directly from space centroids and door connections.

    This is a fallback when Shell.ByFaces() fails (disconnected spaces).
    Creates vertices at space centroids and edges for door connections.

    Args:
        space_shells: Dictionary mapping space_id to Shell/Cluster
        doors: List of door dicts with source_space_id and target_space_id

    Returns:
        Graph or None if creation fails
    """
    _check_topologic_available()
    logger.debug("-" * 40)
    logger.debug("FALLBACK: Building graph from centroids and doors")
    logger.debug("-" * 40)

    if not space_shells:
        logger.debug("  No space shells - cannot build fallback graph")
        return None

    try:
        vertices = []
        space_id_to_vertex: dict[str, Any] = {}

        for space_id, shell in space_shells.items():
            centroid = Topology.Centroid(shell)
            if centroid:
                v_dict = Dictionary.ByKeysValues(["space_id"], [space_id])
                centroid = Topology.SetDictionary(centroid, v_dict)
                vertices.append(centroid)
                space_id_to_vertex[space_id] = centroid
                coords = Vertex.Coordinates(centroid)
                logger.debug(
                    f"  Created vertex for '{space_id}' at ({coords[0]:.2f}, {coords[1]:.2f})")
            else:
                logger.debug(f"  Could not get centroid for '{space_id}'")

        logger.debug(f"  Created {len(vertices)} vertices")

        if not vertices:
            logger.debug("  No vertices created - cannot build graph")
            return None

        edges = []
        for door in doors:
            source_id = door.get("source_space_id")
            target_id = door.get("target_space_id")

            if not source_id or not target_id:
                continue

            source_vertex = space_id_to_vertex.get(source_id)
            target_vertex = space_id_to_vertex.get(target_id)

            if source_vertex and target_vertex:
                edge = Edge.ByVertices([source_vertex, target_vertex])
                if edge:
                    edges.append(edge)
                    logger.debug(
                        f"  Created edge: '{source_id}' <-> '{target_id}'")
            else:
                missing = []
                if not source_vertex:
                    missing.append(source_id)
                if not target_vertex:
                    missing.append(target_id)
                logger.debug(
                    f"  Skipped door {source_id} -> {target_id}: missing vertices {missing}")

        logger.debug(f"  Created {len(edges)} edges")

        if not edges:
            logger.debug("  No edges - creating graph with isolated vertices")
            graph = Graph.ByVerticesEdges(vertices, [])
        else:
            graph = Graph.ByVerticesEdges(vertices, edges)

        if graph:
            g_vertices = Graph.Vertices(graph)
            g_edges = Graph.Edges(graph)
            logger.debug(
                f"  Fallback graph created: {len(g_vertices) if g_vertices else 0} vertices, "
                f"{len(g_edges) if g_edges else 0} edges")
        else:
            logger.debug("  Graph.ByVerticesEdges() returned None")

        return graph

    except Exception as e:
        logger.error(f"  EXCEPTION in fallback graph building: {e}")
        import traceback
        logger.debug(f"  Traceback: {traceback.format_exc()}")
        return None


def _get_cells_from_grid_shell(grid_shell: Any) -> dict[str, Any]:
    """Extract cell faces from grid shell indexed by cell_id.

    Args:
        grid_shell: Shell containing grid cells with cell_id dictionaries

    Returns:
        Dictionary mapping cell_id to face
    """
    _check_topologic_available()
    cells = {}
    if not grid_shell:
        return cells

    faces = Topology.Faces(grid_shell)
    if not faces:
        logger.debug("  grid_shell has no faces")
        return cells

    for face in faces:
        face_dict = Topology.Dictionary(face)
        if face_dict:
            cell_id = Dictionary.ValueAtKey(face_dict, "cell_id")
            if cell_id:
                cells[cell_id] = face

    logger.debug(f"  Extracted {len(cells)} cells from grid_shell")
    return cells


def _find_door_edges(
    grid_shell: Any,
    doors: list[dict[str, str | None]],
) -> list[Any]:
    """Find shared edges for door connections using grid shell topology.

    Uses Topology.SharedEdges() to find actual topological edges between
    adjacent cells. This ensures apertures work correctly.

    Args:
        grid_shell: Shell containing grid cells (required for SharedEdges)
        doors: List of door dicts with source_cell_id and target_cell_id

    Returns:
        List of door edges with color dictionaries
    """
    _check_topologic_available()
    logger.debug("-" * 40)
    logger.debug("Finding door edges from grid shell")
    logger.debug("-" * 40)

    if not grid_shell:
        logger.warning("  No grid_shell provided - cannot find shared edges")
        return []

    # Get cells indexed by cell_id
    cells = _get_cells_from_grid_shell(grid_shell)
    if not cells:
        logger.warning("  No cells found in grid_shell")
        return []

    door_edges = []
    doors_missing_cell_ids = 0
    doors_not_found = 0
    doors_no_shared_edge = 0

    for i, door in enumerate(doors):
        source_cell_id = door.get("source_cell_id")
        target_cell_id = door.get("target_cell_id")

        # Validate cell_ids are present
        if not source_cell_id or not target_cell_id:
            logger.warning(
                f"  Door[{i}] missing cell_id "
                f"(source={source_cell_id}, target={target_cell_id})"
            )
            doors_missing_cell_ids += 1
            continue

        # Get cell faces from grid shell
        source_cell = cells.get(source_cell_id)
        target_cell = cells.get(target_cell_id)

        if not source_cell or not target_cell:
            missing = []
            if not source_cell:
                missing.append(source_cell_id)
            if not target_cell:
                missing.append(target_cell_id)
            logger.warning(
                f"  Door[{i}] cell(s) not found in grid: {missing}"
            )
            doors_not_found += 1
            continue

        # Find shared edge between adjacent cells
        shared = Topology.SharedEdges(source_cell, target_cell)
        if shared:
            for edge in shared:
                # Add red color and door info to edge dictionary
                edge_dict = Dictionary.ByKeysValues(
                    ["color", "door", "source_cell", "target_cell"],
                    ["red", f"{source_cell_id}->{target_cell_id}",
                     source_cell_id, target_cell_id]
                )
                edge = Topology.SetDictionary(edge, edge_dict)
                door_edges.append(edge)
            logger.debug(
                f"  Door[{i}]: Found {len(shared)} shared edge(s) between "
                f"{source_cell_id} and {target_cell_id}"
            )
        else:
            logger.warning(
                f"  Door[{i}]: No shared edge between {source_cell_id} and {target_cell_id} "
                f"(cells may not be adjacent)"
            )
            doors_no_shared_edge += 1

    logger.debug(f"  Total door edges found: {len(door_edges)}")
    if doors_missing_cell_ids > 0:
        logger.warning(f"  {doors_missing_cell_ids} doors missing cell_ids")
    if doors_not_found > 0:
        logger.warning(f"  {doors_not_found} doors with cells not in grid")
    if doors_no_shared_edge > 0:
        logger.warning(f"  {doors_no_shared_edge} doors with no shared edge")

    return door_edges


def build_connectivity_graph(
    space_shells: dict[str, Any],
    doors: list[dict[str, str | None]],
    grid_shell: Any,
) -> tuple[Any | None, Any | None]:
    """Build unified shell with door apertures and connectivity graph.

    Creates a topologicpy Graph representing door connections between spaces.
    Doors are modeled as apertures on shared edges, then Graph.ByTopology()
    with viaSharedApertures=True creates the connectivity graph.

    Steps:
    1. Find door edges using SharedEdges on grid_shell (requires grid topology)
    2. Convert space shells to faces using Face.ByShell()
    3. Create unified shell from all space faces
    4. Transfer dictionaries to unified shell using centroid selectors
    5. Add door edges as apertures to unified shell
    6. Create graph using Graph.ByTopology(viaSharedApertures=True)

    Args:
        space_shells: Dictionary mapping space_id to Shell/Cluster
        doors: List of door dicts with source_cell_id and target_cell_id
        grid_shell: Shell containing grid cells with cell_id dictionaries
                    (REQUIRED for finding shared edges)

    Returns:
        Tuple of (unified_shell, graph) or (None, None) if creation fails
    """
    _check_topologic_available()
    logger.debug("=" * 60)
    logger.debug("build_connectivity_graph: START")
    logger.debug("=" * 60)

    # Log input parameters
    logger.debug(
        f"INPUT space_shells: {len(space_shells) if space_shells else 0} spaces")
    if space_shells:
        for space_id, shell in space_shells.items():
            logger.debug(f"  space '{space_id}':")
            _log_topology_info(shell, "shell")

    logger.debug(f"INPUT doors: {len(doors) if doors else 0} doors")
    if doors:
        for i, door in enumerate(doors):
            logger.debug(f"  door[{i}]: {door}")

    logger.debug("INPUT grid_shell:")
    _log_topology_info(grid_shell, "grid_shell")

    if not space_shells:
        logger.debug("EARLY EXIT: space_shells is empty")
        return None, None

    try:
        # Step 1: Find door edges using SharedEdges on grid_shell
        logger.debug("-" * 40)
        logger.debug("STEP 1: Find door edges from grid shell")
        logger.debug("-" * 40)
        door_edges = _find_door_edges(grid_shell, doors)

        # Step 2: Convert space shells to faces
        logger.debug("-" * 40)
        logger.debug("STEP 2: Convert space shells to faces")
        logger.debug("-" * 40)
        space_faces = []
        for space_id, shell in space_shells.items():
            logger.debug(f"Processing space '{space_id}'...")

            # Check if it's a fragmented space (Cluster) - skip these
            shell_dict = Topology.Dictionary(shell)
            is_fragmented = (
                Dictionary.ValueAtKey(shell_dict, "is_fragmented")
                if shell_dict
                else False
            )
            if is_fragmented:
                logger.debug(f"  SKIPPED: fragmented space (Cluster)")
                continue

            logger.debug(f"  calling Face.ByShell()...")
            face = Face.ByShell(shell)
            if face:
                logger.debug(f"  Face.ByShell() SUCCESS")
                _log_topology_info(face, f"face for {space_id}")

                # Transfer space_id to the face
                face_dict = Dictionary.ByKeysValues(["space_id"], [space_id])
                face = Topology.SetDictionary(face, face_dict)
                space_faces.append(face)
            else:
                logger.debug(f"  Face.ByShell() FAILED - returned None")

        logger.debug(f"STEP 2 RESULT: {len(space_faces)} space faces created")

        if not space_faces:
            logger.warning("No space faces created - using fallback graph")
            graph = _build_fallback_graph(space_shells, doors)
            return None, graph

        # Step 3: Create unified shell from space faces
        logger.debug("-" * 40)
        logger.debug("STEP 3: Create unified shell from space faces")
        logger.debug("-" * 40)
        logger.debug(
            f"  calling Shell.ByFaces() with {len(space_faces)} faces...")

        unified_shell = Shell.ByFaces(space_faces)
        if not unified_shell:
            logger.warning(
                "Shell.ByFaces() FAILED - using fallback graph construction")
            graph = _build_fallback_graph(space_shells, doors)
            return None, graph

        logger.debug("Shell.ByFaces() SUCCESS")
        _log_topology_info(unified_shell, "unified_shell")

        # Step 4: Transfer dictionaries to unified shell using centroid selectors
        logger.debug("-" * 40)
        logger.debug("STEP 4: Transfer dictionaries to unified shell")
        logger.debug("-" * 40)
        try:
            selectors = [
                Topology.SetDictionary(
                    Topology.Centroid(f), Topology.Dictionary(f))
                for f in space_faces
            ]
            unified_shell = Topology.TransferDictionariesBySelectors(
                unified_shell,
                selectors,
                tranFaces=True,
                tranEdges=True
            )
            logger.debug("  TransferDictionariesBySelectors() SUCCESS")
            _log_topology_info(
                unified_shell, "unified_shell after dict transfer")
        except Exception as e:
            logger.warning(f"  TransferDictionariesBySelectors() FAILED: {e}")
            import traceback
            logger.debug(f"  Traceback: {traceback.format_exc()}")

        # Validate dictionary transfer
        logger.debug("  Validating dictionary transfer...")
        shell_faces = Shell.Faces(unified_shell) if unified_shell else []
        missing_space_id_count = 0
        for face in shell_faces:
            face_dict = Topology.Dictionary(face)
            space_id = None
            if face_dict:
                keys = Dictionary.Keys(face_dict)
                if keys and "space_id" in keys:
                    space_id = Dictionary.ValueAtKey(face_dict, "space_id")
            if not space_id:
                missing_space_id_count += 1
                try:
                    centroid = Topology.Centroid(face)
                    coords = Vertex.Coordinates(centroid)
                    logger.warning(
                        f"    Face at ({coords[0]:.2f}, {coords[1]:.2f}) missing space_id"
                    )
                except Exception:
                    logger.warning(
                        "    Face missing space_id (could not get coordinates)")

        if missing_space_id_count > 0:
            logger.error(
                f"  {missing_space_id_count}/{len(shell_faces)} faces missing space_id"
            )
        else:
            logger.debug(f"  All {len(shell_faces)} faces have space_id")

        # Step 5: Add door edges as apertures to unified shell
        logger.debug("-" * 40)
        logger.debug("STEP 5: Add apertures to unified shell")
        logger.debug("-" * 40)
        if door_edges:
            logger.debug(f"  Adding {len(door_edges)} apertures...")
            try:
                # Log door edges
                for i, edge in enumerate(door_edges):
                    edge_dict = Topology.Dictionary(edge)
                    door_info = Dictionary.ValueAtKey(
                        edge_dict, "door") if edge_dict else "?"
                    edge_vertices = Topology.Vertices(edge)
                    if edge_vertices and len(edge_vertices) >= 2:
                        v1 = Vertex.Coordinates(edge_vertices[0])
                        v2 = Vertex.Coordinates(edge_vertices[1])
                        logger.debug(
                            f"    [{i}] {door_info}: ({v1[0]:.2f}, {v1[1]:.2f}) -> ({v2[0]:.2f}, {v2[1]:.2f})")

                unified_shell = Topology.AddApertures(
                    unified_shell,
                    door_edges,
                    exclusive=False,
                    subTopologyType="edge"
                )
                logger.debug("  Topology.AddApertures() SUCCESS")

                # Verify apertures were added
                apertures = Topology.Apertures(unified_shell)
                logger.debug(
                    f"  Verification: unified_shell has {len(apertures) if apertures else 0} apertures")

            except Exception as e:
                logger.warning(f"  Topology.AddApertures() FAILED: {e}")
                import traceback
                logger.debug(f"  Traceback: {traceback.format_exc()}")
        else:
            logger.debug("  No door edges - skipping aperture step")

        # Step 6: Create connectivity graph
        logger.debug("-" * 40)
        logger.debug("STEP 6: Create connectivity graph")
        logger.debug("-" * 40)
        logger.debug(
            "  calling Graph.ByTopology(direct=False, viaSharedApertures=True)...")
        graph = Graph.ByTopology(
            unified_shell,
            direct=False,
            viaSharedApertures=True,
            viaSharedTopologies=False
        )

        if graph:
            logger.debug("  Graph.ByTopology() SUCCESS")
            vertices = Graph.Vertices(graph)
            edges = Graph.Edges(graph)
            logger.debug(
                f"  Graph has {len(vertices) if vertices else 0} vertices "
                f"and {len(edges) if edges else 0} edges")

            # Log vertex details
            if vertices:
                logger.debug("  Graph vertices:")
                for i, v in enumerate(vertices):
                    v_dict = Topology.Dictionary(v)
                    keys = Dictionary.Keys(v_dict) if v_dict else []
                    values = [Dictionary.ValueAtKey(v_dict, key)
                              for key in keys] if v_dict else []
                    for key, value in zip(keys, values):
                        logger.debug(f"    [{i}] {key}: {value}")
                    logger.debug(f"    ---")

            # Log edge details
            if edges:
                logger.debug("  Graph edges (connections):")
                for i, edge in enumerate(edges):
                    edge_verts = Topology.Vertices(edge)
                    if edge_verts and len(edge_verts) >= 2:
                        v1 = Vertex.Coordinates(edge_verts[0])
                        v2 = Vertex.Coordinates(edge_verts[1])
                        logger.debug(
                            f"    [{i}] ({v1[0]:.2f}, {v1[1]:.2f}) <-> ({v2[0]:.2f}, {v2[1]:.2f})")
        else:
            logger.warning("  Graph.ByTopology() FAILED - returned None")
            return unified_shell, None

        logger.debug("=" * 60)
        logger.debug("build_connectivity_graph: END (SUCCESS)")
        logger.debug("=" * 60)
        return unified_shell, graph

    except Exception as e:
        logger.error(f"EXCEPTION in build_connectivity_graph: {e}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None, None
