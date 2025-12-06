# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 30-Second Quick Reference

**First time here?** Read this section and "Essential Commands" only, then explore on-demand.

- **Run full pipeline:** `uv run python scripts/run_optimized_pipeline.py --band all`
- **Single band test:** `uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy`
- **Available bands:** `billy` | `eggy` | `goose` | `phish` | `um` | `wsp`
- **Web UI:** `uv run streamlit run src/jambandnerd/web/app.py`
- **Run tests:** `pytest tests/`
- **Critical concept:** All feature engineering uses `reference_date` cutoff to prevent data leakage

**When stuck:** Check "Triage Matrix" section below.

---

## Project Overview

JamBandNerd is a cloud-based data science platform for collecting, transforming, and predicting jam band setlists. The system handles multiple bands (Widespread Panic, Phish, Umphrey's McGee, Goose, Billy Strings, Eggy) through a unified, band-agnostic architecture that flows from data sources → collection → transformation → prediction → evaluation → web interface.

**Core Mission**: Generate accurate next-song predictions and setlist structure forecasts through automated data pipelines, supporting both scheduled automation and on-demand analysis.

## Essential Commands

### Environment Setup
```bash
# Create and activate Python 3.12 virtual environment
uv venv --python=3.12
source .venv/bin/activate
uv pip install .

# Development dependencies
uv pip install -e ".[dev]"

# Documentation dependencies
uv pip install -e ".[docs]"
mkdocs serve  # Serve docs locally
```

### Running the Pipeline
```bash
# Primary pipeline command (recommended)
uv run python scripts/run_optimized_pipeline.py --band all
uv run python scripts/run_optimized_pipeline.py --band goose
uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy

# Generate predictions for specific band/model
uv run python scripts/generate_predictions.py --band phish --model ckplus
uv run python scripts/generate_predictions.py --band goose --model notebook --date 2024-08-01

# Run backtests (accuracy evaluation)
uv run python scripts/run_backtest.py --band goose --model notebook --shows 50
```

### Testing & Code Quality
```bash
pytest tests/                    # Run all tests
pytest tests/test_models.py      # Run specific test file
ruff check src/                  # Lint code
black src/                       # Format code
```

### Web Interface
```bash
uv run streamlit run src/jambandnerd/web/app.py
```

## Architecture

### Data Flow Pipeline
```
Band Sources → Collection (API/Scrape) → Raw Storage (Supabase) →
In-Memory Transform → Models (Notebook/CK+) → Predictions (Supabase) →
Evaluation → Web Interface
```

### Key Design Principles

1. **Band-Agnostic Core**: The transformation pipeline (`src/jambandnerd/transformations/gaps.py`) and prediction models work identically across all bands. Band-specific logic is isolated to collectors.

2. **In-Memory Transformation**: No intermediate tables. Raw data from Supabase is transformed in-memory into the `ModelData` container, which feeds prediction models.

3. **Reference Date as Anti-Leakage Guard**: All feature engineering respects a `reference_date` cutoff to prevent data leakage during backtesting and evaluation.

4. **Pluggable Model Architecture**: Models inherit from `PredictionModel` base class (src/jambandnerd/models/base.py). Two current implementations:
   - **Notebook Model**: Frequency-based with gap analysis
   - **CK+ Model**: Enhanced algorithm with additional features

5. **Dynamic Band Discovery**: The pipeline automatically discovers supported bands by scanning for `run_*_collection.py` scripts in `scripts/`. To add a new band, create a new collection script following existing patterns.

### Core Components

#### Data Collection (`src/jambandnerd/data_collection/`)
- **Base Classes**: `BaseCollector` (base.py) provides rate limiting, retries, and session management
- **Band-Specific Collectors**: Each band has its own collector (e.g., `goose/collector.py`, `phish/collector.py`)
  - API-based: Phish (phish.net), Goose (elgoose.net)
  - Scraping-based: WSP (everydaycompanion.com + TourWrangler fallback), UM (allthings.umphreys.com)
- **Output**: Standardized schemas stored in Supabase tables: `{band}_shows_raw`, `{band}_setlists_raw`

#### Transformations (`src/jambandnerd/transformations/`)
- **Core Module**: `gaps.py` contains `generate_model_data()` which produces `ModelData` containers
- **Features**: Gap analysis, recency, rotation metrics, position-specific priors (openers/closers), recently played tracking
- **ModelData Container**: Holds `historical_plays`, `master_feature_set`, `reference_date`, `reference_index`, `recently_played_songs`, and `diagnostics`

#### Models (`src/jambandnerd/models/`)
- **Base**: `base.py` defines `PredictionModel` abstract class with `predict()` method
- **Implementations**:
  - `notebook/model.py`: `NotebookPredictor`
  - `ckplus/model.py`: `CKPlusPredictor`
- **Accuracy Evaluation**: `accuracy.py` contains centralized accuracy calculation (Top-K hit rate, MRR)

#### Database (`src/jambandnerd/db/`)
- **Connection**: `connection.py` - Singleton Supabase client with Streamlit secrets fallback
- **Operations**: `operations.py` - `upsert_dataframe()`, table operations
- **Validation**: `validation.py` - Schema validation and data quality checks

#### Web Interface (`src/jambandnerd/web/`)
- **Entry Point**: `app.py` - Streamlit application
- **Features**: Multi-band selection, model comparison, live predictions, accuracy visualization, show details

### Script Organization

Scripts in `scripts/` directory:
- **Collection**: `run_{band}_collection.py` - Band-specific data collection entry points
- **Unified Pipeline**: `run_optimized_pipeline.py` - Orchestrates collection → transform → predict → evaluate
- **Prediction**: `generate_predictions.py` - Unified prediction generator accepting `--band` and `--model`
- **Evaluation**: `run_backtest.py` - Calculates accuracy metrics via backtesting
- **Utilities**: `common.py` (shared functions), `get_all_bands.py` (dynamic band discovery)

## Important Data Patterns

### Environment Variables
Required in `.env` file:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service key
- `PHISH_API_KEY` - Optional, only for Phish data collection

### Schema Conventions
- Raw tables: `{band}_shows_raw`, `{band}_setlists_raw`
- Prediction tables: Cross-band unified `predictions`, `backtest_accuracy`
- Required columns in raw shows: `show_date`, `venue`, `city`, `state`
- Required columns in raw setlists: `show_date`, `set_number`, `song_name`, `song_position`

### WSP Special Handling
WSP collector scrapes everydaycompanion.com but includes TourWrangler.com as fallback for recent shows. When EC publishes the official setlist, it automatically replaces TourWrangler data (see `src/jambandnerd/data_collection/wsp/tourwrangler.py` and `wsp/orchestration.py`).

### Rate Limiting & Retries
All collectors inherit exponential backoff with configurable retry logic from `BaseCollector`. Default: 3 retries, 2.0x backoff factor, 30s timeout. WSP has additional anti-ban measures with randomized delays.

## GitHub Actions Automation

The platform runs automated daily pipelines via `.github/workflows/daily-pipeline.yml`:
- **Schedule**: 19:00 UTC daily (3 PM ET during DST)
- **Dynamic Matrix**: Automatically discovers bands via `scripts/get_all_bands.py`
- **Manual Triggers**: Supports on-demand execution with band selection
- **Parallel Execution**: Each band runs as a separate matrix job with `fail-fast: false`
- **Secret Management**: Injects `SUPABASE_URL`, `SUPABASE_KEY`, `PHISH_API_KEY` from GitHub secrets

## Development Workflow

### Adding a New Band

1. Create band-specific collector in `src/jambandnerd/data_collection/{band}/collector.py` inheriting from `BaseCollector`
2. Create collection script `scripts/run_{band}_collection.py` with entry point function
3. Ensure Supabase tables exist: `{band}_shows_raw`, `{band}_setlists_raw` with standard schemas
4. Test with: `uv run python scripts/run_{band}_collection.py`
5. Validate predictions: `uv run python scripts/generate_predictions.py --band {band} --model notebook`
6. Pipeline will auto-discover the new band on next GitHub Actions run

### Modifying Models

- Models must implement `predict(model_data: ModelData, top_k: int) -> PredictionResult`
- Accuracy evaluation is handled externally by `src/jambandnerd/models/accuracy.py` for consistency
- Add new model by creating `src/jambandnerd/models/{model_name}/model.py` and updating `generate_predictions.py`

### Data Leakage Prevention

**Critical**: All feature engineering in `transformations/gaps.py` uses `reference_date` to filter historical data. When creating features or modifying the pipeline:
- Never include data after `reference_date` in training features
- Use `shows_df[shows_df["show_date"] < reference_date]` filtering pattern
- Backtesting simulates predictions as-of historical dates; leakage invalidates evaluation

### Testing New Features

```bash
# Test data collection
pytest tests/test_collectors.py -v

# Test model predictions with diagnostics
uv run python scripts/generate_predictions.py --band goose --model notebook

# Validate prediction outputs
uv run python scripts/validate_prediction_tables.py --band goose

# Run backtest for accuracy
uv run python scripts/run_backtest.py --band goose --model notebook --shows 10
```

## Common Patterns & Gotchas

### When Adding Features to Transformations
- Update `generate_model_data()` in `src/jambandnerd/transformations/gaps.py`
- Ensure new features respect `reference_date` cutoff
- Add to `master_feature_set` DataFrame if song-level aggregation
- Update `diagnostics` dict if helpful for debugging

### When Working with Supabase
- Use `src/jambandnerd/db/operations.upsert_dataframe()` for bulk writes
- Primary keys for raw tables: `(band, show_date)` for shows, `(band, show_date, set_number, song_position)` for setlists
- Predictions table uses `(band, model, reference_date)` as primary key

### Debugging Pipeline Failures
1. Check `scripts/diagnose_band_data.py --band {band}` for data quality issues
2. Verify raw data freshness: `python scripts/verify_data_freshness.py --band {band}`
3. Enable debug output in `generate_model_data()`: `debug=True` parameter
4. Check GitHub Actions logs for error traces in matrix jobs

## Prediction Success Metrics

- **Top-K Hit Rate**: Did the actual next song appear in top K predictions? (K=1, K=10, K=25, K=50)
- **Mean Reciprocal Rank (MRR)**: Average of 1/rank where rank is position of correct song
- **Baseline Comparison**: Lift over naive rotation baseline (predict by days-since-played)
- **Per-Band Evaluation**: Stored in `backtest_accuracy` table, visualized in web app

## Triage Matrix (When Something Breaks)

| Issue Type | First Check | Common Solutions |
|------------|-------------|------------------|
| **Install/env errors** | Python 3.12? UV installed? | `uv venv --python=3.12 && uv pip install .` |
| **Collection failures** | API keys in .env? Rate limits? | Check `src/jambandnerd/data_collection/base.py` retry logic |
| **Prediction errors** | Raw tables populated? | Run `scripts/diagnose_band_data.py --band {band}` |
| **Data leakage suspected** | Reference date filtering? | Verify `transformations/gaps.py` uses `reference_date` cutoff |
| **Accuracy regressions** | Recent feature changes? | Run backtest: `scripts/run_backtest.py --band {band} --shows 10` |
| **Web UI issues** | Supabase connection? Data freshness? | Check `verify_data_freshness.py`, browser console |
| **GitHub Actions failures** | Secrets configured? | Check `.github/workflows/daily-pipeline.yml` env vars |

## Common Anti-Patterns to Avoid

**Don't:**
- ❌ Add features to `transformations/gaps.py` without respecting `reference_date` cutoff
- ❌ Create new intermediate Supabase tables (use in-memory transforms)
- ❌ Hardcode band names (use dynamic discovery via `get_all_bands.py`)
- ❌ Invent commands not in README.md or this file
- ❌ Skip testing after model changes (always run backtest)
- ❌ Commit without running `ruff check` and `black`
- ❌ Modify raw table schemas without updating all band collectors
- ❌ Add band-specific logic to transformation pipeline (keep collectors isolated)

**Do:**
- ✅ Use `scripts/run_optimized_pipeline.py` for end-to-end testing
- ✅ Add `--skip-accuracy` flag for faster iteration
- ✅ Check diagnostics output from `generate_model_data(debug=True)`
- ✅ Run smallest useful command first, then iterate
- ✅ Update both `ModelData` container and model if adding features
- ✅ Follow existing collector patterns when adding new bands

## Project-Specific Context

- **Python 3.12 Required**: Project uses Python 3.12 features, do not use 3.13+
- **UV Package Manager**: Preferred over pip for dependency management
- **Supabase Backend**: All persistent storage uses Supabase PostgreSQL + auth
- **No Local Data Files**: Data flows through Supabase; no `data/` directory artifacts in production
- **Idempotent Collectors**: Re-running collectors overwrites existing data for the same dates
- **Context Budget**: When exploring code, load files on-demand rather than scanning entire directories

---

**Version:** 2025-12-01
**Maintained by:** JamBandNerd core team
