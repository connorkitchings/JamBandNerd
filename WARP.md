# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

JamBandNerd is a cloud-based data science platform for collecting, transforming, and predicting jam band setlists. The system operates with modular pipelines that collect data from APIs/scraping, transform it in-memory, run prediction models, and store results in Supabase.

**Supported Bands**: Goose (elgoose.net API), Phish (phish.net API), Widespread Panic (planned)  
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

#### Goose Pipeline (Primary)

```bash
# 1. Collect raw data
uv run python scripts/run_goose_collection.py
uv run python scripts/run_goose_collection.py --skip-validation  # bypass schema validation

# 2. Generate predictions (defaults to next upcoming show)
uv run python scripts/generate_goose_predictions.py
uv run python scripts/generate_goose_predictions.py --date YYYY-MM-DD  # historical date

# 3. Generate CK+ model predictions  
uv run python scripts/generate_goose_ckplus_predictions.py

# 4. Backtest accuracy over time window
uv run python scripts/backtest_goose_notebook.py --start 2025-06-01 --end 2025-08-16
uv run python scripts/backtest_goose_ckplus.py --start 2025-06-01 --end 2025-08-16

# 5. Save accuracy summaries (last N completed shows)
uv run python scripts/save_notebook_accuracy.py --shows 50
uv run python scripts/save_ckplus_accuracy.py --shows 50
```

#### Phish Pipeline

```bash
# Collect all Phish data
uv run python scripts/run_phish_collection.py

# Collect only setlists for specific years (faster when shows are current)
uv run python scripts/run_phish_collection.py --only-setlists --year-start 2024 --year-end 2025 --skip-validation

# Clear and rebuild setlists (DESTRUCTIVE)
uv run python scripts/run_phish_collection.py --clear-setlists --only-setlists --year-start 1983 --year-end 1989 --skip-validation

# Generate predictions
uv run python scripts/generate_phish_predictions.py
uv run python scripts/generate_phish_ckplus_predictions.py
```

### Development Commands

```bash
# Code quality
ruff check src/  # linting
black src/       # formatting
pytest tests/    # run tests (when available)

# Web interface (planned)
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
2. Create prediction script: `scripts/generate_{band}_{model}_predictions.py`
3. Add backtest script: `scripts/backtest_{band}_{model}.py`  
4. Define accuracy table: `accuracy_{model}`

### Critical Environment Dependencies

**Python 3.12+** (lxml 4.9.3 pinned for stability)  
**UV Package Manager** (used throughout scripts and README)
**Supabase** (primary database, requires URL/KEY in .env)  
**External APIs**:

- elgoose.net (no auth required)
- phish.net (requires PHISH_API_KEY)
- Planned: everydaycompanion.com scraping

### Development Guidelines from .cursorrules

- **Data Integrity**: Idempotent collectors with stable keys, source hashing, duplicate detection
- **Rate Limiting**: Exponential backoff on 429/5xx, respect robots.txt, cache raw responses
- **Feature Engineering Focus**: Rotation/recency, position priors, tour/venue effects, segues
- **Validation Requirements**: Schema validation, completeness checks, no future data leakage
- **Band-Agnostic Design**: Common schemas and interfaces across all supported bands
