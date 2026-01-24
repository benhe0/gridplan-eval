"""Data models for evaluation results (stub - to be implemented)."""

from enum import Enum
from pydantic import BaseModel
from typing import Any
from datetime import datetime


class ConstraintStatus(str, Enum):
    """Status of constraint evaluation."""

    EVALUATED = "evaluated"  # Normal evaluation completed
    SKIPPED = "skipped"  # Could not evaluate (e.g., missing space type)

    def __str__(self) -> str:
        return self.value


class ConstraintResult(BaseModel):
    """Result of evaluating a single constraint instance."""

    constraint_id: str
    constraint_type: str
    passed: bool
    status: ConstraintStatus = ConstraintStatus.EVALUATED
    metadata: dict[str, Any]

    class Config:
        frozen = True


class EvaluationResult(BaseModel):
    """Complete evaluation result."""

    floor_plan_id: str
    config_file: str
    timestamp: datetime
    model_name: str | None = None
    constraints_total: int
    constraints_passed: int
    constraints_skipped: int = 0
    results: list[ConstraintResult]
    execution_time_ms: float

    @property
    def constraints_failed(self) -> int:
        return self.constraints_total - self.constraints_passed

    def to_summary_dict(self) -> dict:
        """Summary stats for quick inspection."""
        return {
            "floor_plan_id": self.floor_plan_id,
            "passed": self.constraints_passed,
            "total": self.constraints_total,
            "failed": self.constraints_failed,
            "skipped": self.constraints_skipped,
        }
