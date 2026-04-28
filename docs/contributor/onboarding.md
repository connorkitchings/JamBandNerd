# Onboarding Guide

Welcome to the JamBandNerd project! This guide will help you get set up and make your first contribution.

## 1. Project Overview

JamBandNerd is a data platform for collecting, transforming, and predicting jam band setlists. The project is built around Python pipeline code and Supabase-backed storage, and it is now moving toward a website-first frontend strategy.

The project is designed to be modular and extensible, but the core data
architecture is intentionally strict:

- raw ingestion stays source-faithful
- shared transforms and models consume a normalized internal contract
- prediction logic is organized around ordered shows and setlists

Read the [Architecture](developer_guide/architecture.md) page first, then use
the [Data Strategy](../reference/specifications/data_strategy.md) page as the
source of truth for ingestion/storage/prediction contracts.

## 2. Getting Started

### Prerequisites

- Python 3.12+
- `uv` package manager
- Git
- A Supabase account (for database access)

### Installation

Please follow the installation instructions in the [README.md](https://github.com/connorkitchings/JamBandNerd/blob/main/README.md) to set up your local environment. This will guide you through cloning the repository, setting up the virtual environment, and installing the required dependencies.

### Environment Variables

Before you can run the project, create a `.env` file in the project root with:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `PHISH_API_KEY` (optional, for Phish data only)

For the website, copy the example env file:

```bash
cp apps/web/.env.local.example apps/web/.env.local
```

Then fill in `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `apps/web/.env.local`.

## 3. Development Workflow

The project follows a modular development approach. Each major component (data collection, transformation, modeling) is designed to be self-contained. This makes it straightforward to add new bands or prediction models by following the existing patterns.

### Key Directories

- `apps/web/`: The website application.
- `src/jambandnerd/`: The main source code for the project.
  - `data_collection/`: Band-specific data collectors.
  - `db/`: Database connection and operations.
  - `models/`: Prediction models and accuracy calculations.
  - `transformations/`: Data transformation and feature engineering.
- `scripts/`: Standalone scripts for running the data pipelines.
- `docs/`: Project documentation.
- `tests/`: Unit and integration tests.

### Running the Tests

Before you make any changes, it's a good idea to run the existing tests to make sure everything is working correctly.

```bash
npm run verify:python
```

### Making Changes

1. **Create a new branch**: Create a new branch for your changes.
2. **Write your code**: Make your changes to the code, following the existing style and conventions.
3. **Write tests**: If you are adding new functionality, please add corresponding tests.
4. **Update documentation**: If your changes affect the documentation, please update it accordingly.
5. **Run the linter and formatter**: Before you commit your changes, run the canonical health checks to ensure your code follows the project's style guide.

    ```bash
    npm run verify:python
    npm run verify:docs
    ```

For website work, also run:

```bash
npx playwright install --with-deps chromium
npm run verify:web
```

For a final stability pass on a clean baseline, also run:

```bash
npm run verify:clean
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
2. Persist the required raw entities: shows, setlists, and songs.
3. Ensure normalization can expose a stable `show_id`, `show_date`, and
   show-ordering contract to shared transforms.
4. Wire the band into the current local orchestration paths and validate it
   through the consolidated prediction and backtest scripts.
5. Confirm automation can discover or execute the collector correctly.

## 6. How to Add a New Model

To add a new prediction model, you will need to:

1. Create a new model in `src/jambandnerd/models/`.
2. Consume the existing `ModelData` contract rather than creating a
   band-specific transform path.
3. Wire the model into the consolidated prediction and evaluation flow.
4. Add tests and backtest validation for the new model.
5. Update storage/docs if the model becomes a supported public option.
