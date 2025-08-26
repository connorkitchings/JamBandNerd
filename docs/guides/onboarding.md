# Onboarding Guide

Welcome to the JamBandNerd project! This guide will help you get set up and make your first contribution.

## 1. Project Overview

JamBandNerd is a data science platform for collecting, transforming, and predicting jam band setlists. The project is built with Python and uses Supabase for the database, and Streamlit for the web interface.

The project is designed to be modular and extensible, so you can easily add new bands, models, or features.

## 2. Getting Started

### Prerequisites

- Python 3.12+
- `uv` package manager
- Git
- A Supabase account (for database access)

### Installation

Please follow the installation instructions in the [README.md](../README.md) to set up your local environment. This will guide you through cloning the repository, setting up the virtual environment, and installing the required dependencies.

### Environment Variables

Before you can run the project, you will need to set up your environment variables. Copy the `.env.example` file to a new file named `.env` and fill in the required values for your Supabase project.

## 3. Development Workflow

The project follows a modular development approach. Each major component (data collection, transformation, modeling) is designed to be self-contained. This makes it straightforward to add new bands or prediction models by following the existing patterns.

### Key Directories

- `src/jambandnerd/`: The main source code for the project.
  - `data_collection/`: Band-specific data collectors.
  - `db/`: Database connection and operations.
  - `models/`: Prediction models and accuracy calculations.
  - `transformations/`: Data transformation and feature engineering.
  - `web/`: The Streamlit web application.
- `scripts/`: Standalone scripts for running the data pipelines.
- `docs/`: Project documentation.
- `tests/`: Unit and integration tests.

### Running the Tests

Before you make any changes, it's a good idea to run the existing tests to make sure everything is working correctly.

```bash
pytest
```

### Making Changes

1.  **Create a new branch**: Create a new branch for your changes.
2.  **Write your code**: Make your changes to the code, following the existing style and conventions.
3.  **Write tests**: If you are adding new functionality, please add corresponding tests.
4.  **Update documentation**: If your changes affect the documentation, please update it accordingly.
5.  **Run the linter and formatter**: Before you commit your changes, run the linter and formatter to ensure your code follows the project's style guide.

    ```bash
    ruff check src/
    black src/
    ```

6.  **Commit your changes**: Commit your changes with a clear and descriptive commit message.
7.  **Push your changes and open a pull request**: Push your changes to your fork and open a pull request against the main repository.

## 4. How to Add a New Band

To add a new band to the project, you will need to:

1.  Create a new data collector for the band in `src/jambandnerd/data_collection/`.
2.  Add the band to the `BAND_CONFIG` in `src/jambandnerd/web/app.py`.
3.  Add the band to the `run_optimized_pipeline.py` script.
4.  Add the band to the GitHub Actions workflow.

## 5. How to Add a New Model

To add a new prediction model, you will need to:

1.  Create a new model in `src/jambandnerd/models/`.
2.  Add the model to the `MODEL_CONFIG` in `src/jambandnerd/web/app.py`.
3.  Create new prediction and accuracy scripts in the `scripts/` directory.
4.  Add the model to the `run_optimized_pipeline.py` script.
5.  Add the model to the GitHub Actions workflow.
