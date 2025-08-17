# Gemini Rules for `cfb_model`

This file defines project rules and conventions for developing and maintaining the College Football
Betting Model. It should be kept in sync with the broader documentation, especially the
[Project Charter](docs/project_org/project_charter.md) and [Development Standards](docs/project_org/development_standards.md).

---

## 1. Data Handling

- **Data Storage:**
  - Data is stored locally, separate from the repository. The root path is defined by the
    `CFB_MODEL_DATA_ROOT` environment variable, typically set in a `.env` file.
  - Raw data is stored in `/data/raw/` and is considered immutable.
  - Processed datasets are stored in `/data/processed/`.
- **Schemas and Transformations:**
  - All data schemas are documented in the [Data Dictionary](docs/guides/data_dictionary.md).
  - All transformations must be documented within the source code and be reproducible. Any
    significant changes to the aggregation logic should be noted in the [Decision Log](docs/decisions/decision_log.md).
- **Column Naming Convention:**
  - Offensive stats: `off_*` (e.g., `off_epa_pp`)
  - Defensive stats: `def_*` (e.g., `def_sr`)
  - Opponent-adjusted stats: `adj_*` (e.g., `adj_off_epa_pp`)
- **Time-based Data:**
  - Always include `season`, `week`, and `game_id` for traceability.
  - Aggregations should include counts of the underlying data (plays, drives, games) for validation.

---

## 2. Modeling Rules

- **No Data Leakage:**
  - Training data must strictly precede prediction data. All season-to-date features are computed up
    to (but not including) the current game.
  - Betting lines must **not** be used as features in the model. They are used only for calculating
    the betting edge.
- **Training Window:**
  - The primary training window is 2014–2023 (excluding 2020). The final holdout test year is 2024.
  - In-season predictions begin after a team has played a minimum of 4 games.
- **Validation:**
  - The primary validation strategy is a train/test split by year.
  - Walk-forward validation may be used for hyperparameter tuning if necessary.
- **Baseline Models:**
  - All new models must be compared against the `Ridge` regression baseline.
- **Model Artifacts:**
  - Trained models are saved to `models/<model_name>/<test_year>/` (e.g., `models/ridge_baseline/2024/`).
  - Evaluation metrics are saved to `reports/metrics/`.

---

## 3. Code Style & Quality

- **Version:** Python 3.12+
- **Tooling:**
  - Use `uv` for environment and package management.
  - Use `ruff` for all formatting and linting. Run `uv run ruff format .` and `uv run ruff check .`
    before committing.
- **Standards:**
  - All new functions must include Google-style docstrings and type hints.
  - Use the `logging` module for output; avoid `print()` in application code.
  - Follow the quality gates defined in the [Checklists](docs/project_org/checklists.md).

---

## 4. AI-Assisted Development

- **Session Start:** Begin each session by providing the minimal context pack as defined in the
  [AI Session Templates](docs/guides/ai_session_templates.md).
- **Clarity:** Be explicit in your requests. Reference specific files and functions.
- **Verification:** Always review and validate AI-generated code. You are ultimately responsible
  for the quality of the output.

---

## 5. Documentation

- All changes to code, data, or workflow must be reflected in the documentation.
- Key documents to keep updated: `README.md`, `docs/project_org/project_charter.md`,
  `docs/project_org/feature_catalog.md`, and the `docs/decisions/decision_log.md`.
