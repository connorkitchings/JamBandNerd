# AI Agent Guidance for JamBandNerd

This file provides general guidance for any AI agent working on the JamBandNerd repository.

## Project Overview

JamBandNerd is a cloud-based data science platform for collecting, transforming, and predicting jam band setlists.

-   **Supported Bands**: Goose, Phish, Widespread Panic, Billy Strings, Umphrey's McGee.
-   **Architecture**: Data Sources → Raw Data (Supabase) → In-Memory Transform → Models → Predictions (Supabase) → Web Interface (Streamlit).
-   **Core Logic**: The main pipeline logic is in `scripts/run_optimized_pipeline.py`, which orchestrates calls to other consolidated scripts like `generate_predictions.py` and `run_backtest.py`.

## Key Files for Context

Before starting work, review the following files to understand the project:

-   **`pyproject.toml`**: Defines project dependencies, scripts, and build configuration. Essential for understanding the `uv` setup.
-   **`README.md`**: High-level project overview, setup, and usage instructions.
-   **`docs/developer_guide/architecture.md`**: Detailed architecture overview.
-   **`src/jambandnerd/config.py`**: Centralized configuration for the project.
-   **`scripts/run_optimized_pipeline.py`**: The main pipeline orchestration script.
-   **`src/jambandnerd/models/`**: The prediction model implementations.

## Essential Commands

### Environment Setup

```bash
# Initial setup
uv venv --python=3.12
source .venv/bin/activate
uv pip install .
```
*Note: Ensure a `.env` file is present with `SUPABASE_URL` and `SUPABASE_KEY`.*

### Running the Pipeline

```bash
# Run the complete pipeline for all supported bands
uv run python scripts/run_optimized_pipeline.py --band all

# Run the pipeline for a single band
uv run python scripts/run_optimized_pipeline.py --band goose
```

### Development Commands

```bash
# Code quality
ruff check src/
black src/
pytest tests/

# Web interface
streamlit run src/jambandnerd/web/app.py
```

## Development Guidelines

-   **Modularity**: The project is highly modular. Follow the existing patterns when adding new collectors, models, or scripts.
-   **Configuration over Code**: Use the centralized configuration in `src/jambandnerd/config.py`. Avoid hardcoding values.
-   **Consolidated Scripts**: The project uses a few powerful, parameterized scripts (e.g., `generate_predictions.py`). Prefer extending these scripts over creating new ones.
-   **Code Style**: Adhere to the project's code style (black, ruff).
-   **Testing**: Add tests for new functionality in the `tests/` directory.
