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

The system is designed with a modular pipeline that processes data in stages:

1. **Data Sources**: External APIs and web scraping sites.
2. **Raw Data**: Data is collected and stored in its raw format in Supabase.
3. **In-Memory Transform**: Raw data is pulled into memory, cleaned, and standardized into features for the models.
4. **Models**: Prediction algorithms (e.g., Notebook, CK+) consume the transformed data.
5. **Predictions**: The model outputs are stored in Supabase.
6. **Web Interface**: A Streamlit app reads the predictions to display them to the user.

### Data Flow (current)

1. **Collection**: APIs/scraping → Raw Supabase tables (`{band}_*_raw`)
2. **Transform**: In-memory transformation for model features
3. **Predict**: Features → predictions stored in Supabase
4. **Accuracy**: Historical backtesting and summary metrics
5. **Display**: (planned) Streamlit UI
6. **Automate**: (planned) GitHub Actions daily run

---

## Unified tables

To simplify queries across bands and models, predictions and accuracy are stored in unified tables:

- `predictions_notebook`: One row per prediction run with a nested `predictions` JSON array and metadata
  - Key fields: `band`, `reference_date`, `model_version`, `top_k`, `predicted_at`
  - Constraint: unique on (`band`, `reference_date`, `model_version`)
- `notebook_accuracy`: Aggregate accuracy summary over a rolling window (e.g., last 50 completed shows)
  - Key fields: `band`, `model_version`, `window_start`, `window_end`, `num_shows`, k10/k25/k50 metrics
- `predictions_ckplus`: Same structure as predictions_notebook, for CK+ model
- `accuracy_ckplus`: Aggregate accuracy summary for CK+

Notes:

- Legacy `goose_notebook_predictions` has been migrated/deprecated; use `predictions_notebook` going forward.
- The Streamlit app and scripts already read/write the unified tables.

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

   Ensure `.env` exists (it is gitignored). MCP/AI handles database setup automatically; no
   local setup script is required.

### Usage

#### Run Pipelines (Goose-first during Phase 2)

Scripts are introduced as the Goose pipeline is implemented. For now, align work with
`documents/planning/implementation_guide.md` and `implementation_schedule.md`. Once available:

```bash
# Run Goose-only pipeline (collect → transform → predict)
python scripts/run_pipeline.py --band goose --collect --predict

# Run all pipelines (when other bands are added later)
python scripts/run_all_pipelines.py
```

#### Run Individual Components

```bash
# Data collection only
python scripts/run_pipeline.py --collect --band phish

# Transform and predict only
python scripts/run_pipeline.py --predict --band goose --model notebook

# Web interface (planned for later phase)
# streamlit run src/jambandnerd/web/app.py
```

---

## Project Structure

```text
JamBandNerd/
├── documents/
│   ├── planning/
│   │   ├── PRD.md
│   │   ├── implementation_guide.md
│   │   ├── implementation_schedule.md
│   │   └── project_context.md
│   ├── data/                   # API/scraping specifications
│   └── execution/
│       └── dev_logs/
├── src/jambandnerd/
│   ├── data_collection/
│   │   └── goose/
│   ├── transformations/
│   ├── models/
│   ├── db/
│   ├── predictions/
│   └── web/                    # planned
├── scripts/                    # planned
└── tests/                      # planned
```

---

## Development

The project is built with a modular architecture to allow for independent development, testing, and
extension. Each major component (data collection, transformation, modeling) is designed to be
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

An interactive web interface for exploring predictions is planned but has not been started.
Planned features include:

- **Band Selection**: Switch between Phish, Goose, and WSP.
- **Model Comparison**: Toggle between Notebook and CK+ models.
- **Prediction Display**: Show next song probabilities and confidence scores.
- **Historical Accuracy**: Visualize model performance over time, with adjustable K (10/25/50).
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
