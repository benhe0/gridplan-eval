"""Topology visualization using topologicpy's Plotly integration.

This module requires the 'viz' extra to be installed:
    pip install gridplan-eval[viz]
"""

import logging
from pathlib import Path
from typing import Any

try:
    from topologicpy.Plotly import Plotly
    from topologicpy.Topology import Topology
    TOPOLOGIC_AVAILABLE = True
except ImportError:
    TOPOLOGIC_AVAILABLE = False
    Plotly = None
    Topology = None

logger = logging.getLogger(__name__)


def _check_topologic_available():
    """Check if topologicpy is available, raise helpful error if not."""
    if not TOPOLOGIC_AVAILABLE:
        raise ImportError(
            "Visualization requires topologicpy and plotly. "
            "Install with: pip install gridplan-eval[viz]"
        )

# Color palette for space types
SPACE_COLORS = {
    'reception': '#FF6B6B',
    'open_work_area': '#4ECDC4',
    'meeting': '#45B7D1',
    'phone_booth': '#96CEB4',
    'kitchen': '#FFEAA7',
    'lounge': '#DDA0DD',
    'bathroom_men': '#87CEEB',
    'bathroom_women': '#FFB6C1',
    'storage': '#D3D3D3',
    'circulation': '#F5F5DC',
}

# Default color for unknown space types
DEFAULT_COLOR = '#CCCCCC'


def _get_color_for_space_type(space_type: str) -> str:
    """Get hex color for a space type."""
    return SPACE_COLORS.get(space_type, DEFAULT_COLOR)


def visualize_floor_plan(
    space_shells: dict[str, Any],
    grid_shell: Any,
    doors: list[dict[str, str | None]],
    space_types: dict[str, str],
    output_path: str | Path,
    title: str = "Floor Plan Topology",
    show_connectivity_graph: bool = True,
) -> bool:
    """Generate an interactive HTML visualization of a floor plan topology.

    Args:
        space_shells: Dictionary mapping space_id to Shell/Cluster
        grid_shell: Shell representing the grid boundary
        doors: List of door dicts with source_space_id, target_space_id, source_cell_id, target_cell_id
        space_types: Dictionary mapping space_id to space type
        output_path: Path to save the HTML file
        title: Title for the visualization
        show_connectivity_graph: Whether to include the connectivity graph overlay

    Returns:
        True if successful, False otherwise
    """
    _check_topologic_available()
    from ..geometry.graph_builder import build_connectivity_graph

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_data = []

    # Add grid boundary (faint outline)
    if grid_shell:
        grid_data = Plotly.DataByTopology(
            grid_shell,
            showFaces=True,
            faceColor='#F8F8F8',
            faceOpacity=0.3,
            showEdges=True,
            edgeColor='#CCCCCC',
            edgeWidth=1,
            showVertices=False,
        )
        all_data.extend(grid_data)

    # Add each space with its color
    for space_id, shell in space_shells.items():
        space_type = space_types.get(space_id, 'unknown')
        color = _get_color_for_space_type(space_type)

        space_data = Plotly.DataByTopology(
            shell,
            showFaces=True,
            faceColor=color,
            faceOpacity=0.8,
            showEdges=True,
            edgeColor='#333333',
            edgeWidth=1,
            showVertices=False,
            faceLabelKey=None,
            showFaceLegend=True,
            faceLegendLabel=f"{space_id} ({space_type})",
        )
        all_data.extend(space_data)

    # Add connectivity graph (door connections)
    if show_connectivity_graph and doors:
        _, graph = build_connectivity_graph(
            space_shells, doors, grid_shell
        )
        if graph:
            graph_data = Plotly.DataByGraph(
                graph,
                vertexColor='#E74C3C',
                vertexSize=10,
                edgeColor='#E74C3C',
                edgeWidth=3,
            )
            if graph_data:
                all_data.extend(graph_data)
                logger.debug("Added connectivity graph to visualization")
            else:
                logger.warning("Plotly.DataByGraph returned None for graph")

    # Create figure
    figure = Plotly.FigureByData(
        all_data,
        width=950,
        height=700,
        backgroundColor='white'
    )

    margin = 0

    dim = 1000

    figure.update_layout(
        width=dim, height=dim,
        margin=dict(t=margin, r=margin, l=margin, b=margin)
    )

    camera = dict(
        up=dict(x=0, y=1, z=0),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=0, y=0, z=1),  # Even smaller to zoom in more
        projection=dict(type="orthographic")
    )

    figure.update_layout(
        scene=dict(
            xaxis=dict(range=[-1, 16], visible=False),  # Wider range
            yaxis=dict(range=[-1, 16], visible=False),
            zaxis=dict(range=[-16, 16], visible=False),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8),
            camera=camera
        )
    )

    # Update title
    figure.update_layout(title=title)

    try:
        # Export to HTML
        figure.write_html(str(output_path), include_plotlyjs='cdn')
        logger.info(f"Saved HTML visualization to {output_path}")
        # Export PDF
        pdf_path = output_path.with_suffix('.pdf')
        figure.write_image(str(pdf_path), format='pdf', width=dim, height=dim)
        logger.info(f"Saved PDF visualization to {pdf_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save visualization: {e}")
        return False


def visualize_from_response(
    response_data: dict,
    grid_rows: int,
    grid_cols: int,
    output_path: str | Path,
) -> bool:
    """Generate visualization directly from a response dictionary.

    Args:
        response_data: Parsed JSON response with allocation and doors
        grid_rows: Number of grid rows
        grid_cols: Number of grid columns
        output_path: Path to save the HTML file

    Returns:
        True if successful, False otherwise
    """
    _check_topologic_available()
    # Import here to avoid circular imports
    from ..run_eval import extract_topology

    floor_plan_id = response_data.get("id", "unnamed")

    space_shells, grid_shell, doors, space_types = extract_topology(
        response_data, grid_rows, grid_cols
    )

    return visualize_floor_plan(
        space_shells=space_shells,
        grid_shell=grid_shell,
        doors=doors,
        space_types=space_types,
        output_path=output_path,
        title=f"Floor Plan: {floor_plan_id}",
    )
