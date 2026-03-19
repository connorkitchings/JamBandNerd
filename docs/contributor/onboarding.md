# Onboarding Guide

Welcome to the JamBandNerd project! This guide will help you get set up and make your first contribution.

## 1. Project Overview

JamBandNerd is a data platform for collecting, transforming, and predicting jam band setlists. The project is built around Python pipeline code and Supabase-backed storage, and it is now moving toward a website-first frontend strategy.

The project is designed to be modular and extensible, so you can easily add new bands, models, or features.

## 2. Getting Started

### Prerequisites

- Python 3.12+
- `uv` package manager
- Git
- A Supabase account (for database access)

### Installation

Please follow the installation instructions in the [README.md](https://github.com/connorkitchings/JamBandNerd/blob/main/README.md) to set up your local environment. This will guide you through cloning the repository, setting up the virtual environment, and installing the required dependencies.

### Environment Variables

Before you can run the project, create a `.env` file in the project root and fill in the required values for your Supabase project.

## 3. Development Workflow

The project follows a modular development approach. Each major component (data collection, transformation, modeling) is designed to be self-contained. This makes it straightforward to add new bands or prediction models by following the existing patterns.

### Key Directories

- `apps/web/`: The primary website application and default frontend target.
- `src/jambandnerd/`: The main source code for the project.
  - `data_collection/`: Band-specific data collectors.
  - `db/`: Database connection and operations.
  - `models/`: Prediction models and accuracy calculations.
  - `transformations/`: Data transformation and feature engineering.
  - `web/`: The legacy Streamlit fallback that remains in the repo during cutover.
- `scripts/`: Standalone scripts for running the data pipelines.
- `docs/`: Project documentation.
- `tests/`: Unit and integration tests.

### Running the Tests

Before you make any changes, it's a good idea to run the existing tests to make sure everything is working correctly.

```bash
uv run pytest
```

### Making Changes

1. **Create a new branch**: Create a new branch for your changes.
2. **Write your code**: Make your changes to the code, following the existing style and conventions.
3. **Write tests**: If you are adding new functionality, please add corresponding tests.
4. **Update documentation**: If your changes affect the documentation, please update it accordingly.
5. **Run the linter and formatter**: Before you commit your changes, run the canonical health checks to ensure your code follows the project's style guide.

    ```bash
    uv run black src tests scripts
    uv run ruff check src tests scripts
    uv run pytest
    ```

For website work, also run:

```bash
npm run lint:web
npm run build:web
```

6. **Commit your changes**: Commit your changes from a feature branch with a clear conventional commit message.
7. **Push your changes and open a pull request**: Push your changes to your fork and open a pull request against the main repository.

## 4. AI-Assisted Workflow

JamBandNerd now uses a canonical AI operating layer for Codex, Claude, and Gemini:

- Start at `AGENTS.md`, which redirects to `.agent/AGENTS.md`
- Read `.agent/CONTEXT.md` after the boot-order files
- Load task workflows from `.agent/skills/CATALOG.md`
- Use `session_logs/` for active AI session logs and handoffs

Historical logs in `docs/logs/` remain available for reference, but they are no longer the active session workflow.

## 5. How to Add a New Band

To add a new band to the project, you will need to:

1. Create a new data collector for the band in `src/jambandnerd/data_collection/`.
2. Ensure the band is discoverable through the `run_{band}_collection.py` pattern in `scripts/`.
3. Validate the band through the consolidated prediction and backtest scripts.
4. Confirm the GitHub Actions workflow will pick it up through dynamic discovery.

## 6. How to Add a New Model

To add a new prediction model, you will need to:

1. Create a new model in `src/jambandnerd/models/`.
2. Wire the model into the consolidated prediction and evaluation flow.
3. Add tests and backtest validation for the new model.
4. Update documentation if the model becomes a supported public option.
