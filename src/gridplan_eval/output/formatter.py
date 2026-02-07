"""Rich-based output formatter for constraint evaluation results."""

from collections import defaultdict

from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from ..models.result import EvaluationResult, ConstraintResult, ConstraintStatus


# Constraint type groupings with display order
CONSTRAINT_GROUPS: dict[str, list[str]] = {
    "Layout Integrity": [
        "grid_bounds",
        "cell_overlap",
        "allocation",
        "global_connectivity",
    ],
    "Space Instances": [
        "presence",
        "area",
        "contiguity",
        "shape",
        "facade_access",
        "min_width",
    ],
    "Connectivity": [
        "adjacency",
        "door",
        "avoidance",
    ],
}

# Display names for constraint types
CONSTRAINT_DISPLAY_NAMES: dict[str, str] = {
    "grid_bounds": "Grid Bounds",
    "cell_overlap": "Cell Overlap",
    "allocation": "Allocation",
    "global_connectivity": "Global Connectivity",
    "presence": "Presence",
    "area": "Area",
    "contiguity": "Contiguity",
    "shape": "Shape",
    "facade_access": "Facade Access",
    "min_width": "Min Width",
    "adjacency": "Adjacency",
    "door": "Door",
    "avoidance": "Avoidance",
}


class LogFormatter:
    """Formats evaluation results as rich tree output.

    Collects all constraint results for a floor plan and renders them
    as a hierarchical tree grouped by constraint type.

    Usage:
        formatter = LogFormatter(quiet=False)

        # After each floor plan evaluation:
        formatter.display_floor_plan_results(evaluation_result)

        # At the end of batch:
        formatter.display_batch_summary(all_results)
    """

    def __init__(self, quiet: bool = False, console: Console | None = None):
        """Initialize formatter.

        Args:
            quiet: If True, suppress all output (matches --quiet behavior)
            console: Optional rich Console instance (for testing)
        """
        self.quiet = quiet
        self.console = console or Console(stderr=True)

    def display_floor_plan_results(self, result: EvaluationResult) -> None:
        """Display results for a single floor plan as a tree.

        Args:
            result: Complete evaluation result for one floor plan
        """
        if self.quiet:
            return

        tree = self._build_result_tree(result)
        self.console.print()
        self.console.print(tree)

    def _build_result_tree(self, result: EvaluationResult) -> Tree:
        """Build a rich Tree from evaluation results.

        Structure:
        Floor Plan: {id} [12/47 passed]
        ├── Layout Integrity [4/4]
        │   ├── [PASS] grid_bounds: All cells within grid [15x15]
        │   └── ...
        ├── Space Instances [6/30]
        │   ├── Presence [10/13]
        │   │   └── ...
        │   └── ...
        └── Connectivity [2/13]
            └── ...
        """
        passed = result.constraints_passed
        total = result.constraints_total

        if passed == total:
            status_style = "bold green"
        elif passed == 0:
            status_style = "bold red"
        else:
            status_style = "bold yellow"

        root_label = Text()
        root_label.append("Floor Plan: ", style="bold")
        root_label.append(result.floor_plan_id, style="cyan")
        root_label.append(" [", style="dim")
        root_label.append(f"{passed}/{total}", style=status_style)
        root_label.append(" passed]", style="dim")

        tree = Tree(root_label)

        # Group results by constraint type
        results_by_type = self._group_results_by_type(result.results)

        # Add each group
        for group_name, constraint_types in CONSTRAINT_GROUPS.items():
            self._add_group_branch(tree, group_name, constraint_types, results_by_type)

        return tree

    def _group_results_by_type(
        self, results: list[ConstraintResult]
    ) -> dict[str, list[ConstraintResult]]:
        """Group constraint results by their constraint_type."""
        grouped: dict[str, list[ConstraintResult]] = defaultdict(list)
        for r in results:
            grouped[r.constraint_type].append(r)
        return grouped

    def _add_group_branch(
        self,
        tree: Tree,
        group_name: str,
        constraint_types: list[str],
        results_by_type: dict[str, list[ConstraintResult]],
    ) -> None:
        """Add a group branch (e.g., 'Layout Integrity') with its constraints."""
        # Collect all results for this group
        group_results: list[ConstraintResult] = []
        for ct in constraint_types:
            group_results.extend(results_by_type.get(ct, []))

        if not group_results:
            return  # Skip empty groups

        # Calculate group stats
        passed = sum(1 for r in group_results if r.passed)
        total = len(group_results)

        # Create group label
        group_label = Text()
        group_label.append(group_name, style="bold")
        group_label.append(f" [{passed}/{total}]", style="dim")

        group_branch = tree.add(group_label)

        # Add constraint types within group
        for constraint_type in constraint_types:
            type_results = results_by_type.get(constraint_type, [])
            if not type_results:
                continue

            self._add_constraint_type_branch(group_branch, constraint_type, type_results)

    def _add_constraint_type_branch(
        self,
        parent: Tree,
        constraint_type: str,
        results: list[ConstraintResult],
    ) -> None:
        """Add a constraint type branch with individual results."""
        display_name = CONSTRAINT_DISPLAY_NAMES.get(constraint_type, constraint_type)

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        # Create type label
        type_label = Text()
        type_label.append(display_name, style="bold dim")
        type_label.append(f" [{passed}/{total}]", style="dim")

        type_branch = parent.add(type_label)

        # Add individual results
        for result in results:
            self._add_result_leaf(type_branch, result)

    def _add_result_leaf(self, parent: Tree, result: ConstraintResult) -> None:
        """Add a single constraint result as a leaf node."""
        # Determine status badge
        if result.status == ConstraintStatus.SKIPPED:
            badge = Text("[SKIP]", style="yellow")
        elif result.passed:
            badge = Text("[PASS]", style="green")
        else:
            badge = Text("[FAIL]", style="red bold")

        # Get reason from metadata
        reason = result.metadata.get("reason", "")

        # Build leaf label
        leaf_label = Text()
        leaf_label.append_text(badge)
        leaf_label.append(" ")
        leaf_label.append(result.constraint_id, style="cyan dim")
        if reason:
            leaf_label.append(": ", style="dim")
            leaf_label.append(reason)

        parent.add(leaf_label)

    def display_batch_summary(self, results: list[EvaluationResult]) -> None:
        """Display summary after processing all floor plans.

        Args:
            results: All evaluation results from the batch
        """
        if self.quiet:
            return

        if not results:
            return

        # Calculate totals
        total_floor_plans = len(results)
        total_constraints = sum(r.constraints_total for r in results)
        total_passed = sum(r.constraints_passed for r in results)
        pass_rate = (total_passed / total_constraints * 100) if total_constraints > 0 else 0

        # Create summary table
        table = Table(title="Evaluation Summary", show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Floor plans evaluated", str(total_floor_plans))
        table.add_row("Total constraints", str(total_constraints))
        table.add_row("Passed", f"{total_passed} ({pass_rate:.1f}%)")
        table.add_row("Failed", str(total_constraints - total_passed))

        self.console.print()
        self.console.print(Panel(table, border_style="blue"))
