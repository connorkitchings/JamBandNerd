# Quick Start

Copy-paste-ready commands for the most common JamBandNerd tasks.

## Setup

```bash
uv venv --python=3.12
source .venv/bin/activate
uv pip install .
uv pip install -e ".[dev]"
```

### Python and Runner Notes

- Required interpreter: Python `3.12.x` (see `pyproject.toml`).
- Preferred runner: `uv run ...`.
- If `uv` panics on your host, use a local `.venv` fallback:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts
python -m pytest
```

## Pipeline

```bash
uv run python scripts/run_optimized_pipeline.py --band all
uv run python scripts/run_optimized_pipeline.py --band goose
uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy
```

## Individual Operations

```bash
uv run python scripts/generate_predictions.py --band goose --model notebook
uv run python scripts/run_backtest.py --band goose --model notebook --shows 50
uv run python scripts/diagnose_band_data.py --band goose
uv run python scripts/verify_data_freshness.py --band goose
```

## Website

```bash
npm install && npm run dev:web
```

## Quality Gates

```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest
```

## Git Workflow

```bash
git branch
git checkout -b feat/<name>
git status
git commit -m "feat: describe change"
```
