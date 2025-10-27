# JamBandNerd

A cloud-based data science platform for collecting, transforming, and predicting jam band setlists. The system provides real-time setlist predictions through automated data pipelines and an interactive web interface.

## Quick Start

### Prerequisites

- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv) (recommended)
- Supabase account and project
- API keys (see Environment Setup below)

### Installation

1.  **Clone and setup environment:**

    ```bash
    git clone https://github.com/connorkitchings/JamBandNerd.git
    cd JamBandNerd
    uv venv --python=3.12
    source .venv/bin/activate
    uv pip install .
    ```

2.  **Environment configuration:**

    Create a `.env` file in the project root with:

    ```bash
    SUPABASE_URL=your_supabase_url
    SUPABASE_KEY=your_supabase_key
    PHISH_API_KEY=your_phish_net_key  # Optional, for Phish data only
    ```

## Usage

### Optimized Pipeline (Recommended)

The primary way to run the data pipeline is with the `run_optimized_pipeline.py` script. This script handles data collection, transformations, predictions, and accuracy calculations for the specified band(s).

```bash
# Run the complete pipeline for all supported bands
uv run python scripts/run_optimized_pipeline.py --band all

# Run the pipeline for a single band (e.g., Goose)
uv run python scripts/run_optimized_pipeline.py --band goose

# Skip accuracy calculations for a faster run
uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
```

### Advanced Usage

While the optimized pipeline is recommended, you can also run individual components for debugging or granular control. The main scripts accept `--band` and `--model` arguments.

```bash
# Generate predictions for a single band and model
'uv run python scripts/generate_predictions.py --band phish --model ckplus'

# Run a backtest to calculate per-show accuracy
'uv run python scripts/run_backtest.py --band goose --model notebook --shows 50'

# Convenience wrappers for Billy Strings predictions
'uv run predict-billy -- --date 2025-10-24'
'uv run predict-billy-ckplus -- --date 2025-10-24'
```

For detailed usage, please refer to the full documentation.

### Web Interface

```bash
# Launch the interactive Streamlit web application
streamlit run src/jambandnerd/web/app.py
```

The web interface provides:

- **Multi-band selection**: Switch between Goose, Phish, Widespread Panic, and Billy Strings.
- **Model comparison**: Toggle between Notebook and CK+ models.
- **Live predictions**: View latest predictions with detailed metrics.
- **Accuracy visualization**: Historical performance charts with configurable K values (K=10/25/50; selected K highlighted).
- **Show details**: Prominent Next Show header with venue, plus model and prediction timestamp.

### Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Code quality
ruff check src/
black src/
pytest tests/
```

## Documentation

For comprehensive documentation, please visit the **[full documentation site](docs/)**.

Key sections include:

- 🚀 **[User Guide](docs/user/getting_started.md)**: For users who want to install, configure, and run the project.
- 🧑‍💻 **[Contributor Guide](docs/contributor/developer_guide/architecture.md)**: For contributors who want to understand the architecture and extend the platform.
- 📚 **[Reference](docs/reference/)**: Detailed technical specifications, schemas, and guides.
- 📈 **[Reports](docs/reports/)**: Summaries of improvements and validation testing.

Generate and serve documentation locally:

```bash
uv pip install -e ".[docs]"
mkdocs serve
```

## Architecture

**Modular Pipeline Design**: Data Sources → Raw Storage → In-Memory Transform → Models → Predictions → Web Interface

**Supported Bands**: Goose (elgoose.net), Phish (phish.net), Widespread Panic (everydaycompanion.com), Billy Strings (bmfsdb.com), and Umphrey's McGee (allthings.umphreys.com).

**Key Components**:

- Band-agnostic data collectors with unified interfaces.
- In-memory transformation pipeline (no intermediate tables).
- Pluggable prediction models (Notebook, CK+).
- Unified cross-band prediction and accuracy storage.
- Supabase backend with automated validation.
- **GitHub Actions automation** with daily pipeline execution.

### Widespread Panic Data & Fallback

The WSP data collector scrapes `everydaycompanion.com`. If a recent historical setlist is missing from EC, the pipeline attempts a backup read from `TourWrangler.com` using a cleaned parser. When EC later publishes the setlist, the EC data will automatically replace the TourWrangler data, ensuring the highest quality data is used.

### Automation

The platform features comprehensive automation through GitHub Actions:

- **Daily Pipeline**: Runs automatically at 3 PM ET every day.
- **Multi-Strategy**: Choice between optimized single-script or parallel multi-step execution.
- **Manual Triggers**: On-demand execution with band selection via GitHub UI (goose/phish/wsp/all).
- **Error Resilience**: Parallel matrix execution with graceful failure handling.
- **Secret Management**: Secure API key and database credential handling.

## Contributing

See [Implementation Guide](docs/guides/implementation.md) for development workflow and current priorities.

## License

MIT
