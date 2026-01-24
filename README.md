# gridplan-eval

A constraint evaluation framework for grid-based spatial planning and floor plan layouts.

## Installation

### Basic installation (pure Python, networkx-based)

```bash
pip install gridplan-eval
```

### Full installation with topologicpy support

```bash
pip install gridplan-eval[topologic]
```

### With visualization support

```bash
pip install gridplan-eval[viz]
```

### Development installation

```bash
pip install gridplan-eval[dev]
```

## Quick Start

```python
from gridplan_eval import Evaluator, EvaluationResult

# Load configuration and create evaluator
evaluator = Evaluator("config.yaml")

# Evaluate a floor plan (using grid-based geometry - no topologicpy required)
result = evaluator.evaluate(
    space_shells=space_shells,
    grid_shell=grid_shell,
    doors=doors,
    space_types=space_types,
)

print(f"Passed: {result.constraints_passed}/{result.constraints_total}")

# Export results
from gridplan_eval.export import save_json, save_csv
save_json(result, "result.json")
save_csv([result], "results.csv")
```

## CLI Usage

### Evaluate floor plans from JSONL

```bash
gridplan-eval responses.jsonl config.yaml -o output_dir
```

### Sanitize LLM responses

```bash
gridplan-sanitize input.jsonl output.jsonl
```

## Configuration

Configuration is done via YAML files. Example:

```yaml
grid:
  width: 15
  height: 15

# Use 'grid' for pure Python (no topologicpy needed)
# Use 'topologic' for topologicpy-based geometry
geometry_engine: "grid"

spaces:
  bedroom:
    count: 2
    min_area: 10
    facade_access: required

connectivity:
  - bedroom adjacent_to bathroom
  - bedroom door_to circulation
```

## Geometry Engines

The framework supports two geometry engines:

1. **grid** (default): Pure Python implementation using networkx. No external dependencies.
2. **topologic**: Uses topologicpy for advanced topological operations. Requires `pip install gridplan-eval[topologic]`.

## Features

- Binary pass/fail constraint evaluation
- Support for multiple space types
- Connectivity constraints (adjacency, doors, avoidance)
- Area and count constraints
- Shape and contiguity constraints
- Facade access constraints
- JSON and CSV export
- Resume capability for batch evaluation
- Streaming evaluation mode

## License

MIT License
