# Gemini Guidance for JamBandNerd

This file provides guidance for Gemini when working on the JamBandNerd repository.

## Project Overview

JamBandNerd is a cloud-based data science platform for collecting, transforming, and predicting jam band setlists.

-   **Supported Bands**: Goose, Phish, Widespread Panic, Billy Strings, Umphrey's McGee.
-   **Architecture**: Data Sources → Raw Data (Supabase) → In-Memory Transform → Models → Predictions (Supabase) → Web Interface (Streamlit).
-   **Core Logic**: The main pipeline logic is in `scripts/run_optimized_pipeline.py`, which calls other consolidated scripts like `generate_predictions.py` and `run_backtest.py`.

## Key Files to Review

-   **`pyproject.toml`**: Defines project dependencies, scripts, and build configuration. Essential for understanding the `uv` setup.
-   **`README.md`**: High-level project overview, setup, and usage.
-   **`docs/developer_guide/architecture.md`**: Detailed architecture overview.
-   **`src/jambandnerd/config.py`**: Centralized configuration for the project.
-   **`scripts/run_optimized_pipeline.py`**: The main pipeline orchestration script.
-   **`src/jambandnerd/models/`**: The prediction model implementations.

## Development Guidelines

-   **Modularity**: Follow the existing modular design. New features should be implemented in a way that is extensible.
-   **Configuration**: Use the centralized configuration in `src/jambandnerd/config.py`. Do not hardcode values.
-   **Code Style**: Adhere to the project's code style (black, ruff). Run `ruff check src/` and `black src/` before committing.
-   **Testing**: Add tests for new functionality in the `tests/` directory.