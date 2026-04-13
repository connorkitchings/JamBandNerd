# Testing Guide

JamBandNerd has two main verification surfaces:

- Python tests under `tests/`
- Website smoke tests for `apps/web`

## Structure

- `tests/data_collection/` - collector- and source-specific tests
- `tests/models/` - model registry, readiness, and predictor behavior
- `tests/pipeline/` - consolidated script and orchestration coverage
- top-level `tests/test_*.py` - shared utilities, db, diagnostics, and support scripts
- `conftest.py` - shared fixtures and test environment setup

## Canonical Commands

```bash
# Inventory the Python suite
uv run pytest --collect-only -q

# Run the full Python suite
uv run pytest

# Run common targeted suites
uv run pytest tests/models tests/pipeline/test_run_backtest.py tests/pipeline/test_run_optimized_pipeline.py

# Inventory the website smoke suite
npm run test:web:smoke:list

# Run website smoke coverage
npm run test:web:smoke
```

## Notes

- Use `uv run ...` for Python commands.
- Live-band or environment-dependent tests are explicitly marked; most of the
  suite is designed to run without touching production services.
- Website smoke coverage is the canonical frontend verification path and is also
  exercised in GitHub Actions.
