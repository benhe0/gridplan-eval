"""Configuration schema for constraint_eval_v2.

Declarative YAML configuration format for floor plan constraint evaluation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# Instance ID pattern: {type}_{number} where type is lowercase with underscores, number >= 1
# Examples: bedroom_1, open_work_area_2, bathroom_men_1
INSTANCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_[1-9][0-9]*$")


class GridConfig(BaseModel):
    """Grid dimensions configuration."""

    width: int = Field(gt=0, description="Grid width in cells")
    height: int = Field(gt=0, description="Grid height in cells")


class SpaceConfig(BaseModel):
    """Configuration for a space instance.

    Each space instance is defined explicitly with its own constraints.
    Instance IDs must follow the pattern {type}_{number} (e.g., bedroom_1, kitchen_2).
    """

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
    """Connectivity rule between space instances.

    Rules specify explicit relationships between named instances,
    e.g., 'bedroom_1 adjacent_to bathroom_1'.
    """

    source: str = Field(description="Source space instance ID")
    relation: ConnectionType = Field(description="Type of relationship")
    target: str = Field(description="Target space instance ID")

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
    """Complete evaluation configuration.

    Spaces are defined as explicit instances with IDs following the pattern
    {type}_{number} (e.g., bedroom_1, kitchen_2). Connectivity rules reference
    these instance IDs directly.
    """

    grid: GridConfig = Field(description="Grid dimensions")
    spaces: dict[str, SpaceConfig] = Field(description="Space instance definitions")
    connectivity: list[str] = Field(
        default_factory=list, description="Connectivity rules in 'instance_id relation instance_id' format"
    )
    geometry_engine: Literal["topologic", "grid"] = Field(
        default="topologic",
        description="Geometry engine to use: 'topologic' (topologicpy) or 'grid' (pure Python + networkx)"
    )

    @field_validator("spaces", mode="after")
    @classmethod
    def validate_instance_ids(cls, spaces: dict[str, SpaceConfig]) -> dict[str, SpaceConfig]:
        """Validate that all space keys are valid instance IDs."""
        for space_id in spaces.keys():
            if not INSTANCE_ID_PATTERN.match(space_id):
                raise ValueError(
                    f"Invalid space instance ID '{space_id}'. "
                    f"Must match pattern '{{type}}_{{number}}' where type is lowercase "
                    f"(with optional underscores) and number >= 1 (e.g., 'bedroom_1', 'open_work_area_2')"
                )
        return spaces

    @model_validator(mode="after")
    def validate_connectivity_references(self) -> "EvalConfig":
        """Validate that connectivity rules reference defined instances."""
        defined_ids = set(self.spaces.keys())

        for rule_str in self.connectivity:
            rule = ConnectivityRule.from_string(rule_str)
            if rule.source not in defined_ids:
                raise ValueError(
                    f"Connectivity rule references undefined space instance '{rule.source}'. "
                    f"Defined instances: {sorted(defined_ids)}"
                )
            if rule.target not in defined_ids:
                raise ValueError(
                    f"Connectivity rule references undefined space instance '{rule.target}'. "
                    f"Defined instances: {sorted(defined_ids)}"
                )

        return self

    def get_connectivity_rules(self) -> list[ConnectivityRule]:
        """Get parsed ConnectivityRule objects.

        Returns:
            List of ConnectivityRule instances
        """
        return [ConnectivityRule.from_string(rule_str) for rule_str in self.connectivity]

    def get_instance_ids(self) -> list[str]:
        """Get all defined instance IDs.

        Returns:
            List of instance IDs
        """
        return list(self.spaces.keys())

    def get_instances_by_type(self, space_type: str) -> dict[str, SpaceConfig]:
        """Get all instances of a given type.

        Args:
            space_type: Type to filter by (e.g., "bedroom")

        Returns:
            Dictionary mapping instance_id to SpaceConfig for matching instances
        """
        result = {}
        for instance_id, config in self.spaces.items():
            if extract_type_from_instance_id(instance_id) == space_type:
                result[instance_id] = config
        return result


def extract_type_from_instance_id(instance_id: str) -> str:
    """Extract space type from instance ID.

    Instance IDs follow pattern {type}_{number} (e.g., 'bedroom_1' -> 'bedroom').

    Args:
        instance_id: Instance ID to parse

    Returns:
        Space type portion of the ID
    """
    parts = instance_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return instance_id
