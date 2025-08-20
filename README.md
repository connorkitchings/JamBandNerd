# JamBandNerd

## Project Overview

JamBandNerd v2 is a cloud-based data science platform for collecting, transforming, and predicting
jam band setlists. The system provides real-time setlist predictions through automated data
pipelines and an interactive web interface.

### Supported Bands

- **Phish** (phish.net API)
- **Goose** (elgoose.net API)
- **Widespread Panic** (everydaycompanion.com scraping)

### Key Features

- **Automated daily data collection** from APIs and web scraping
- **Cloud-native architecture** with Supabase backend
- **Real-time data transformation** pipelines
- **Multiple prediction models** with accuracy tracking
- **Interactive web interface** for exploring predictions
- **Modular pipeline design** for independent component updates
- **Error monitoring** with email notifications

---

## Architecture Overview

```text
Data Sources → Raw Data (Supabase) → In-Memory Transform → Models → Predictions (Supabase) → Web Interface
     ↓              ↓                       ↓                ↓           ↓                    ↓
  phish.net     phish_shows_raw        Standardize         Notebook   predictions_notebook   Streamlit
  elgoose.net   goose_setlists_raw       Format              Model      notebook_accuracy        App
  scraping      wsp_songs_raw             ↓                  CK+                          Band/Model
                                         Common             Model                         Selection
                                         Schema
```

### Data Flow

1. **Collection**: APIs/scraping → Raw Supabase tables (`{band}_*_raw`)
2. **Transform (In-Memory)**: Raw data is loaded into memory, standardized, and used to generate
   model features. No intermediate standardized tables are created.
3. **Predict**: Features → predictions stored in unified tables (e.g., `predictions_notebook`)
4. **Accuracy**: Backtests summarized to unified tables (e.g., `notebook_accuracy`)
5. **Display**: Streamlit web interface
6. **Automate**: GitHub Actions daily run

---

## Quick Start

### Prerequisites

- Python 3.12+
- Supabase account and project
- API keys (see Environment Setup)

### Installation

1. **Clone and setup environment:**

   ```bash
   git clone https://github.com/connorkitchings/JamBandNerd.git
   cd JamBandNerd
   uv venv --python=3.12
   source .venv/bin/activate
   uv pip install .
   ```

2. **Environment configuration:**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # SUPABASE_URL=your_supabase_url
   # SUPABASE_KEY=your_supabase_key
   # PHISH_API_KEY=your_phish_net_key
   ```

3. **Environment variables:**

   Ensure `.env` exists (it is gitignored). MCP/AI handles database setup automatically; no local
   setup script is required.

### Usage

#### Goose pipeline (current)

```bash
# 1) Collect Goose raw data into Supabase
uv run python scripts/run_goose_collection.py

# 2) Generate top-50 predictions for the next/selected show and save to Supabase
uv run python scripts/generate_goose_predictions.py            # defaults to today/next
uv run python scripts/generate_goose_predictions.py --date YYYY-MM-DD

# 3) Backtest historical accuracy over a window
uv run python scripts/backtest_goose_notebook.py --start 2025-06-01 --end 2025-08-16

# 4) Save summary accuracy metrics (last 50 completed shows)
uv run python scripts/save_notebook_accuracy.py
```

---

## Project Structure

```text
JamBandNerd/
├── docs/
│   ├── models/                 # model docs (e.g., notebook.md)
│   ├── project/                # PRD, schedule, ADR
│   ├── guides/                 # ai_sessions, implementation, supabase_api_guide
│   ├── schemas/                # API schemas
│   └── logs/                   # session logs
├── src/jambandnerd/
│   ├── data_collection/
│   │   └── goose/
│   ├── transformations/
│   ├── models/
│   ├── db/
│   └── predictions/
├── scripts/
│   ├── run_goose_collection.py
│   ├── generate_goose_predictions.py
│   ├── backtest_goose_notebook.py
│   └── save_notebook_accuracy.py
└── tests/
```

---

## Development

The project is built with a modular architecture to allow for independent development, testing,
and extension. Each major component (data collection, transformation, modeling) is designed to be
self-contained. This structure makes it straightforward to add new bands or prediction models by
following the existing patterns.

### Modular Architecture

Each component is independently runnable:

- **Data Collection**: Band-specific collectors with unified interface
- **Transformations**: Standardization pipeline for model input
- **Models**: Pluggable prediction models with common API
- **Database**: Abstracted Supabase operations
- **Web Interface**: Model/band selection with historical comparisons

### Adding New Bands

1. Create collector in `src/jambandnerd/data_collection/{band}/`
2. Define schemas in `docs/supabase_schema/{band}_*.md`
3. Add transformation logic in `src/jambandnerd/transformations/`
4. Update web interface band selection

### Adding New Models

1. Implement model in `src/jambandnerd/models/{model_name}/`
2. Follow common prediction interface
3. Add accuracy tracking metrics
4. Update web interface model selection

---

## Web Interface Features

An interactive web interface for exploring predictions is planned but has not been started. Planned
features include:

- **Band Selection**: Switch between Phish, Goose, and WSP.
- **Model Comparison**: Toggle between Notebook and CK+ models.
- **Prediction Display**: Show next song probabilities and confidence scores.
- **Historical Accuracy**: Visualize model performance over time.
- **Full Setlist Predictions**: Generate predictions for an entire show.
- **Interactive Setlist Builder**: Allow users to create and test prediction scenarios.
- **Real-time Show Tracking**: Update predictions as a show progresses.

---

## Automation

### Daily Pipeline (planned)

Automation via GitHub Actions will be added after the Goose pipeline is verified.

### Error Handling

- API failures: Continue with existing data, send notification
- Scraping issues: Retry with backoff, email on persistent failure
- Data validation: Log issues, continue pipeline where possible

---

## Contributing

1. Check the implementation guide for current development priorities
2. Follow modular architecture - changes should be isolated
3. Test individual components before integration
4. Update relevant documentation

---

## License

MIT

---

## References

- [phish.net API](https://phish.net/)
- [elgoose.net API](https://elgoose.net/)
- [Widespread Panic Archive](http://www.everydaycompanion.com/)
- [Supabase Documentation](https://supabase.com/docs)
