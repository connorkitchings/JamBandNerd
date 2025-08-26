# JamBandNerd

A cloud-based data science platform for collecting, transforming, and predicting jam band setlists. The system provides real-time setlist predictions through automated data pipelines and an interactive web interface.

## Quick Start

### Prerequisites

- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv) (recommended)
- Supabase account and project
- API keys (see Environment Setup below)

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

For comprehensive documentation including architecture, API specifications, and development guides:

- 📚 **[Complete Documentation](docs/)** - Full project documentation
- 🏗️ **[Technical Architecture](docs/specifications/technical_overview.md)** - System design and components
- 📋 **[Product Requirements](docs/project/prd.md)** - Features, goals, and specifications  
- 🚀 **[Implementation Guide](docs/guides/implementation.md)** - Development workflow
- 📊 **[Database Schemas](docs/schemas/)** - API and database specifications
- 📖 **[Model Documentation](docs/models/index.md)** - Prediction algorithm details

Generate and serve documentation locally:
```bash
uv pip install -e ".[docs]"
mkdocs serve
```

## Architecture

**Modular Pipeline Design**: Data Sources → Raw Storage → In-Memory Transform → Models → Predictions → Web Interface

**Supported Bands**: Goose (elgoose.net), Phish (phish.net), Widespread Panic (planned)

**Key Components**:
- Band-agnostic data collectors with unified interfaces
- In-memory transformation pipeline (no intermediate tables)
- Pluggable prediction models (Notebook, CK+)
- Unified cross-band prediction and accuracy storage
- Supabase backend with automated validation

## Contributing

See [Implementation Guide](docs/guides/implementation.md) for development workflow and current priorities.

## License

MIT
