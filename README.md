# JamBandNerd

## Project Overview

JamBandNerd v2 is a cloud-based data science platform for collecting, transforming, and predicting jam band setlists. The system provides real-time setlist predictions through automated data pipelines and an interactive web interface.

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
Data Sources → Raw Data (Supabase) → Transform → Models → Predictions (Supabase) → Web Interface
     ↓              ↓                    ↓         ↓           ↓                    ↓
  phish.net     phish_shows         Standardize  Notebook   phish_predictions   Streamlit
  elgoose.net   goose_setlists        Format     Model      goose_predictions     App
  scraping      wsp_songs              ↓          ↓           wsp_predictions      ↓
                                    Common         CK+                          Band/Model
                                    Schema        Model                         Selection
```

### Data Flow

1. **Collection**: APIs/scraping → Raw Supabase tables (`{band}_shows`, `{band}_songs`, etc.)
2. **Transform**: Raw data → Standardized format (in-memory processing)
3. **Predict**: Standardized data → Model predictions → Prediction tables
4. **Display**: Supabase predictions → Streamlit web interface
5. **Automate**: GitHub Actions runs full pipeline daily

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

3. **Initialize database:**

   ```bash
   python scripts/setup_database.py
   ```

### Usage

#### Run Full Pipeline

```bash
python scripts/run_pipeline.py --all
```

#### Run Individual Components

```bash
# Data collection only
python scripts/run_pipeline.py --collect --band phish

# Transform and predict only
python scripts/run_pipeline.py --predict --band goose --model notebook

# Launch web interface
streamlit run src/jambandnerd/web/app.py
```

---

## Project Structure

```text
JamBandNerd/
├── docs/
│   ├── data_sources/          # API/scraping specifications
│   ├── supabase_schema/       # Database table schemas
│   ├── prd.md                 # Product requirements
│   ├── technical_specs.md     # System architecture
│   └── implementation_guide.md # Development roadmap
├── src/jambandnerd/
│   ├── data_collection/       # Band-specific collectors
│   │   ├── phish/
│   │   ├── goose/
│   │   └── wsp/
│   ├── transformations/       # Data standardization
│   ├── models/                # Prediction models
│   │   ├── notebook/
│   │   └── ckplus/
│   ├── database/              # Supabase utilities
│   ├── web/                   # Streamlit application
│   └── utils/                 # Shared utilities
├── scripts/                   # Pipeline orchestration
├── .github/workflows/         # Automation configs
└── tests/                     # Test suites
```

---

## Development

The project is built with a modular architecture to allow for independent development, testing, and extension. Each major component (data collection, transformation, modeling) is designed to be self-contained. This structure makes it straightforward to add new bands or prediction models by following the existing patterns.

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

An interactive web interface for exploring predictions is planned but has not been started. Planned features include:

- **Band Selection**: Switch between Phish, Goose, and WSP.
- **Model Comparison**: Toggle between Notebook and CK+ models.
- **Prediction Display**: Show next song probabilities and confidence scores.
- **Historical Accuracy**: Visualize model performance over time.
- **Full Setlist Predictions**: Generate predictions for an entire show.
- **Interactive Setlist Builder**: Allow users to create and test prediction scenarios.
- **Real-time Show Tracking**: Update predictions as a show progresses.

---

## Automation

### Daily Pipeline

GitHub Actions automatically runs:

1. Data collection for all bands
2. Data transformation and standardization
3. Model predictions generation
4. Error notification emails

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
