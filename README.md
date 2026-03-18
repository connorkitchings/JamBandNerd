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

# Run the pipeline for Eggy
uv run python scripts/run_optimized_pipeline.py --band eggy

# Skip accuracy calculations for a faster run
uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
```

### Advanced Usage

While the optimized pipeline is recommended, you can also run individual components for debugging or granular control. The main scripts accept `--band` and `--model` arguments.

```bash
# Generate predictions for a single band and model
uv run python scripts/generate_predictions.py --band phish --model ckplus

# Run a backtest to calculate per-show accuracy
uv run python scripts/run_backtest.py --band goose --model notebook --shows 50

# Backfill Eggy raw tables without validation warnings
uv run python scripts/run_eggy_collection.py --skip-validation

# Convenience wrappers for Billy Strings predictions
uv run predict-billy -- --date 2025-10-24
uv run predict-billy-ckplus -- --date 2025-10-24
```

For detailed usage, please refer to the full documentation.

### Web Interface

```bash
# Launch the interactive Streamlit web application
uv run streamlit run src/jambandnerd/web/app.py
```

The web interface provides:

- **Multi-band selection**: Switch between all dynamically discovered bands.
- **Model comparison**: Toggle between Notebook and CK+ models.
- **Live predictions**: View latest predictions with detailed metrics.
- **Historical Explorer**: Browse past shows to view predictions vs. actual setlists for specific dates.
- **Accuracy visualization**: Historical performance charts with configurable K values (K=10/25/50; selected K highlighted).
- **Show details**: Prominent Next Show header with venue, plus model and prediction timestamp.

### Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Code quality
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest
```

### Security Maintenance

The repo now has two separate dependency-safety controls:

- **Dependabot** watches the `uv` lockfile and GitHub Actions versions, with the Supabase Python packages grouped into a single update PR.
- **Dependency Audit** is a standalone GitHub Actions workflow that exports the locked Python dependency set and audits it with `pip-audit`.

Manual local audit command:

```bash
tmpfile=$(mktemp /tmp/jbn-audit.XXXXXX)
uv export --format requirements-txt --locked --no-hashes --no-emit-project --output-file "$tmpfile"
uv run --with pip-audit python -m pip_audit -r "$tmpfile" --cache-dir /tmp/pip-audit-cache --no-deps --disable-pip
```

This audit is intentionally separate from the daily pipeline so dependency findings do not block data collection and publishing.

## AI Tools

JamBandNerd now uses a canonical multi-tool agent workflow:

- `AGENTS.md` -> `.agent/AGENTS.md`
- `.agent/CONTEXT.md` for the startup router
- `.agent/skills/CATALOG.md` for task workflows
- `.codex/QUICKSTART.md` for copy-paste commands
- `session_logs/` for active AI handoffs and session notes

Historical logs in `docs/logs/` remain available as archive only.

## Documentation

For comprehensive documentation, please visit the **[full documentation site](docs/)**.

Key sections include:

- 🚀 **[User Guide](docs/user/getting_started.md)**: For users who want to install, configure, and run the project.
- 🧑‍💻 **[Contributor Guide](docs/contributor/onboarding.md)**: For contributors who want the development workflow, architecture, and agentic operating model.
- 📚 **[Reference](docs/reference/)**: Detailed technical specifications, schemas, and guides.
- 📈 **[Reports](docs/reports/)**: Summaries of improvements and validation testing.

Generate and serve documentation locally:

```bash
uv pip install -e ".[docs]"
mkdocs serve
```

## Architecture

**Modular Pipeline Design**: Data Sources → Raw Storage → In-Memory Transform → Models → Predictions → Web Interface

**Supported Bands**: The pipeline dynamically discovers supported bands by looking for `run_*_collection.py` scripts in the `scripts/` directory. To add a new band, simply create a new collection script following the existing pattern.

**Key Components**:

- Band-agnostic data collectors with unified interfaces.
- In-memory transformation pipeline (no intermediate tables).
- Pluggable prediction models (Notebook, CK+).
- Unified cross-band prediction and accuracy storage.
- Supabase backend with automated validation.
- **GitHub Actions automation** with daily pipeline execution.

### Widespread Panic Data & Fallback

The WSP data collector scrapes `everydaycompanion.com`. This process is enhanced with browser automation (Playwright) to ensure high reliability even against sophisticated bot detection. If a recent historical setlist is missing from EC, the pipeline attempts a backup read from `TourWrangler.com` using a cleaned parser. When EC later publishes the setlist, the EC data will automatically replace the TourWrangler data, ensuring the highest quality data is used.

### Automation

The platform features comprehensive automation through GitHub Actions:

- **Daily Pipeline**: Runs automatically at 3 PM ET every day.
- **Dynamic Matrix**: The pipeline automatically discovers and runs for all supported bands.
- **Manual Triggers**: On-demand execution with band selection via the GitHub UI.
- **Error Resilience**: Parallel matrix execution with graceful failure handling.
- **Secret Management**: Secure API key and database credential handling.
- **Optional Notifications**: Discord webhook alerts can be re-enabled via a `notify-discord` job in `.github/workflows/daily-pipeline.yml` if needed.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow overview and [docs/contributor/onboarding.md](docs/contributor/onboarding.md) for contributor-specific orientation.

## License

MIT
