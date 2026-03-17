# Quick Start

Copy-paste-ready commands for the most common JamBandNerd tasks.

## Setup

```bash
uv venv --python=3.12
source .venv/bin/activate
uv pip install .
uv pip install -e ".[dev]"
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

## Web App

```bash
uv run streamlit run src/jambandnerd/web/app.py
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
