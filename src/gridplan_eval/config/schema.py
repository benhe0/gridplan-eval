"""Configuration schema for constraint_eval_v2.

Declarative YAML configuration format for floor plan constraint evaluation.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GridConfig(BaseModel):
    """Grid dimensions configuration."""

    width: int = Field(gt=0, description="Grid width in cells")
    height: int = Field(gt=0, description="Grid height in cells")


class SpaceConfig(BaseModel):
    """Configuration for a space type."""

    count: int = Field(ge=1, description="Number of instances required")
    min_area: int | None = Field(default=None, ge=1, description="Minimum area in cells")
    max_area: int | None = Field(default=None, ge=1, description="Maximum area in cells")
    contiguous: bool = Field(default=True, description="Must be a single connected region")
    facade_access: Literal["required", "avoid"] | None = Field(
        default=None, description="Facade access requirement"
    )
    min_width: int | None = Field(default=None, ge=1, description="Minimum width in cells")
    shape: Literal["rectangular"] | None = Field(default=None, description="Shape constraint")


class ConnectionType(str, Enum):
    """Types of connectivity relationships between spaces."""

    ADJACENT_TO = "adjacent_to"
    DOOR_TO = "door_to"
    AVOID = "avoid"


class ConnectivityRule(BaseModel):
    """Connectivity rule between space types."""

    source: str = Field(description="Source space type")
    relation: ConnectionType = Field(description="Type of relationship")
    target: str = Field(description="Target space type")

    @classmethod
    def from_string(cls, rule_str: str) -> ConnectivityRule:
        """Parse 'bedroom adjacent_to bathroom' format.

        Args:
            rule_str: Rule in format 'source relation target'

        Returns:
            ConnectivityRule instance

        Raises:
            ValueError: If format is invalid or relation type unknown
        """
        parts = rule_str.split()
        if len(parts) != 3:
            raise ValueError(f"Invalid rule format: '{rule_str}'. Expected 'source relation target'")

        source, relation_str, target = parts

        try:
            relation = ConnectionType(relation_str)
        except ValueError:
            valid_relations = [ct.value for ct in ConnectionType]
            raise ValueError(
                f"Unknown relation '{relation_str}'. Valid relations: {valid_relations}"
            )

        return cls(source=source, relation=relation, target=target)


class EvalConfig(BaseModel):
    """Complete evaluation configuration."""

    grid: GridConfig = Field(description="Grid dimensions")
    spaces: dict[str, SpaceConfig] = Field(description="Space type definitions")
    connectivity: list[str] = Field(
        default_factory=list, description="Connectivity rules in 'source relation target' format"
    )
    geometry_engine: Literal["topologic", "grid"] = Field(
        default="topologic",
        description="Geometry engine to use: 'topologic' (topologicpy) or 'grid' (pure Python + networkx)"
    )

    @field_validator("connectivity", mode="after")
    @classmethod
    def validate_connectivity_rules(cls, rules: list[str]) -> list[str]:
        """Validate that all connectivity rules are parseable."""
        for rule_str in rules:
            # This will raise ValueError if invalid
            ConnectivityRule.from_string(rule_str)
        return rules

    def get_connectivity_rules(self) -> list[ConnectivityRule]:
        """Get parsed ConnectivityRule objects.

        Returns:
            List of ConnectivityRule instances
        """
        return [ConnectivityRule.from_string(rule_str) for rule_str in self.connectivity]
