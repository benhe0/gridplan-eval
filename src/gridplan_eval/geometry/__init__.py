"""Geometry abstraction layer."""

from ..geometry.interface import GeometryEngine
from ..geometry.grid_impl import GridGeometry, GridSpace
from ..geometry._factory import create_geometry_engine

# Lazy imports for topologicpy-dependent modules
def __getattr__(name: str):
    if name == "TopologicGeometry":
        from ..geometry.topologic_impl import TopologicGeometry
        return TopologicGeometry
    if name == "build_connectivity_graph":
        from ..geometry.graph_builder import build_connectivity_graph
        return build_connectivity_graph
    if name == "get_grid_cell_by_id":
        from ..grid import get_grid_cell_by_id
        return get_grid_cell_by_id
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "GeometryEngine",
    "TopologicGeometry",
    "GridGeometry",
    "GridSpace",
    "create_geometry_engine",
    "build_connectivity_graph",
    "get_grid_cell_by_id",
]
