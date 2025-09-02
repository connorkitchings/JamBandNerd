# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

JamBandNerd is a cloud-based data science platform for collecting, transforming, and predicting jam band setlists. The system operates with modular pipelines that collect data from APIs/scraping, transform it in-memory, run prediction models, and store results in Supabase.

**Supported Bands**: Goose (elgoose.net API), Phish (phish.net API), Widespread Panic (everydaycompanion.com scraping - 95% complete)  
**Architecture**: Data Sources → Raw Data (Supabase) → In-Memory Transform → Models → Predictions (Supabase) → Web Interface

## Essential Commands

### Environment Setup

```bash
# Initial setup
uv venv --python=3.12
source .venv/bin/activate
uv pip install .

# Required environment variables in .env (gitignored)
# SUPABASE_URL=your_supabase_url
# SUPABASE_KEY=your_supabase_key
# PHISH_API_KEY=your_phish_net_key (for Phish data only)
```

### Data Pipeline Commands

#### Recommended: Optimized Pipeline (All Bands)

```bash
# Run complete pipeline for all supported bands (fastest, most reliable)
uv run python scripts/run_optimized_pipeline.py --band all

# Run pipeline for a single band
uv run python scripts/run_optimized_pipeline.py --band goose
uv run python scripts/run_optimized_pipeline.py --band phish
uv run python scripts/run_optimized_pipeline.py --band wsp

# Skip accuracy calculations for faster runs
uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
```

#### Individual Pipeline Components (Advanced Usage)

##### Data Collection
```bash
# Collect raw data by band
uv run python scripts/run_goose_collection.py
uv run python scripts/run_phish_collection.py
uv run python scripts/run_wsp_collection.py

# Collection with options
uv run python scripts/run_goose_collection.py --skip-validation
uv run python scripts/run_phish_collection.py --only-setlists --year-start 2024 --year-end 2025
uv run python scripts/run_wsp_collection.py --year-start 2023 --year-end 2024
```

##### Prediction Generation (Consolidated Scripts)
```bash
# Generate predictions for any band/model combination
uv run python scripts/generate_predictions.py --band goose --model notebook
uv run python scripts/generate_predictions.py --band goose --model ckplus
uv run python scripts/generate_predictions.py --band phish --model notebook
uv run python scripts/generate_predictions.py --band phish --model ckplus
uv run python scripts/generate_predictions.py --band wsp --model notebook
uv run python scripts/generate_predictions.py --band wsp --model ckplus

# Generate predictions for historical date
uv run python scripts/generate_predictions.py --band goose --model notebook --date 2024-08-15
```

##### Accuracy & Backtesting (Consolidated Scripts)
```bash
# Run historical backtests for any band/model combination
uv run python scripts/run_backtest.py --band goose --model notebook --shows 50
uv run python scripts/run_backtest.py --band goose --model ckplus --shows 50
uv run python scripts/run_backtest.py --band phish --model notebook --start 2024-01-01 --end 2024-08-31

# Save accuracy summaries
uv run python scripts/save_aggregate_accuracy.py --band goose --model notebook --shows 50
uv run python scripts/save_aggregate_accuracy.py --band phish --model ckplus --shows 100
```

### Development Commands

```bash
# Code quality
ruff check src/  # linting
black src/       # formatting
pytest tests/    # run tests (when available)

# Web interface (fully implemented)
streamlit run src/jambandnerd/web/app.py

# Test secrets availability in GitHub Actions
# Use workflow_dispatch on .github/workflows/test_secrets.yml
```

## Code Architecture

### Modular Design Philosophy

The project uses a **modular pipeline architecture** where each component is independently runnable and extensible:

- **Data Collection**: Band-specific collectors inherit from `BandCollector` abstract base class
- **Transformations**: In-memory standardization pipeline (no intermediate storage)  
- **Models**: Pluggable prediction models implementing `PredictionModel` interface
- **Database**: Abstracted Supabase operations with validation
- **Unified Storage**: Cross-band, cross-model prediction and accuracy tables

### Core Abstract Patterns

#### Data Collection (`src/jambandnerd/data_collection/base.py`)

```python
class BandCollector(ABC):
    @abstractmethod
    def collect_shows(self, start_date: date, end_date: date) -> List[Dict[str, Any]]
    def collect_setlists(self, show_ids: List[str]) -> List[Dict[str, Any]]
    def collect_songs(self) -> List[Dict[str, Any]]  
    def collect_venues(self) -> List[Dict[str, Any]]
```

#### Prediction Models (`src/jambandnerd/models/base.py`)

```python
class PredictionModel(ABC):
    @abstractmethod
    def train(self, data: StandardizedData) -> None
    def predict(self, current_setlist: List[str], context: Dict[str, Any]) -> List[Prediction]
    def calculate_accuracy(self, predictions: List[Prediction], actual_songs: List[str]) -> AccuracyMetrics
```

### Data Flow Architecture

1. **Raw Data Layer**: `{band}_*_raw` tables store API/scraping responses with source hashing
2. **In-Memory Transform**: Raw data loaded, cleaned, and standardized for model features  
3. **Unified Predictions**: `predictions_notebook`, `predictions_ckplus` store cross-band results
4. **Unified Accuracy**: `notebook_accuracy`, `accuracy_ckplus` store backtest summaries
5. **Web Interface**: Streamlit app reads unified tables for band/model selection

### Key Implementation Details

#### Database Operations

- **Connection**: Singleton Supabase client via `get_supabase_client()`
- **Validation**: Schema validation with `validate_dataframe_against_table()`
- **Upserts**: Conflict resolution on primary keys with `upsert_dataframe()`
- **Pagination**: Robust chunked fetching via `fetch_table()` in `scripts/common.py`

#### Data Standardization  

- **Schema Normalization**: Column name mapping (e.g., `api_show_id` → `show_id`)
- **Type Coercion**: Date parsing, string conversion, null handling
- **Source Integrity**: SHA256 hashing of raw API responses for change detection
- **Band-Agnostic**: Common schemas across Phish, Goose, etc.

### Extension Patterns

#### Adding New Bands

1. Create collector: `src/jambandnerd/data_collection/{band}/collector.py`
2. Implement `BandCollector` interface  
3. Define raw table schemas: `{band}_shows_raw`, `{band}_setlists_raw`, etc.
4. Add transformation logic in `src/jambandnerd/transformations/`
5. Update unified table writes

#### Adding New Models

1. Implement `PredictionModel`: `src/jambandnerd/models/{model_name}/`
2. Update consolidated scripts to support new model:
   - Add model choice to `scripts/generate_predictions.py`
   - Add model choice to `scripts/run_backtest.py`
   - Add model choice to `scripts/save_aggregate_accuracy.py`
3. Define accuracy table: `accuracy_{model}`
4. Update `run_optimized_pipeline.py` to include new model

### Critical Environment Dependencies

**Python 3.12+** (lxml 4.9.3 pinned for stability)  
**UV Package Manager** (used throughout scripts and README)
**Supabase** (primary database, requires URL/KEY in .env)  
**External APIs**:

- elgoose.net (no auth required)
- phish.net (requires PHISH_API_KEY)
- everydaycompanion.com (WSP scraping - 95% complete)

### Development Guidelines from .cursorrules

- **Data Integrity**: Idempotent collectors with stable keys, source hashing, duplicate detection
- **Rate Limiting**: Exponential backoff on 429/5xx, respect robots.txt, cache raw responses
- **Feature Engineering Focus**: Rotation/recency, position priors, tour/venue effects, segues
- **Validation Requirements**: Schema validation, completeness checks, no future data leakage
- **Band-Agnostic Design**: Common schemas and interfaces across all supported bands
