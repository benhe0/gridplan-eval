"""Factory for creating geometry engine instances."""

from __future__ import annotations

from typing import Literal

from .interface import GeometryEngine


def create_geometry_engine(
    engine_type: Literal["topologic", "grid"],
    grid_rows: int | None = None,
    grid_cols: int | None = None,
) -> GeometryEngine:
    """Create a geometry engine instance based on type.

    Args:
        engine_type: Type of engine - "topologic" or "grid"
        grid_rows: Number of grid rows (required for "grid" engine)
        grid_cols: Number of grid columns (required for "grid" engine)

    Returns:
        GeometryEngine instance

    Raises:
        ValueError: If engine_type is unknown or grid dimensions missing for grid engine
    """
    if engine_type == "topologic":
        try:
            from .topologic_impl import TopologicGeometry
            return TopologicGeometry()
        except ImportError:
            raise ImportError(
                "Topologic geometry engine requires topologicpy. "
                "Install with: pip install gridplan-eval[topologic] "
                "or use geometry_engine: 'grid' in your config."
            )

    elif engine_type == "grid":
        if grid_rows is None or grid_cols is None:
            raise ValueError(
                "grid_rows and grid_cols are required for 'grid' geometry engine"
            )
        from .grid_impl import GridGeometry
        return GridGeometry(grid_rows=grid_rows, grid_cols=grid_cols)

    else:
        raise ValueError(
            f"Unknown geometry engine type: {engine_type}. "
            "Valid options are 'topologic' or 'grid'"
        )
