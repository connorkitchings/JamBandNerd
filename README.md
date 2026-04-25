# JamBandNerd

A cloud-based data platform for collecting, transforming, and predicting jam band setlists. The system provides real-time setlist predictions through automated pipelines, Supabase-backed storage, and a website-first product roadmap.

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
    SUPABASE_SERVICE_ROLE_KEY=your_pipeline_service_role_key
    PHISH_API_KEY=your_phish_net_key  # Optional, for Phish data only
    FG_USER_EMAIL=your_fantasy_goose_login  # Optional, for Fantasy Goose automation
    FG_PASSWORD=your_fantasy_goose_password  # Optional, for Fantasy Goose automation
    ```

    For the website, use `apps/web/.env.local` with:

    ```bash
    SUPABASE_URL=your_supabase_url
    SUPABASE_ANON_KEY=your_supabase_anon_key
    ```

## Usage

### Optimized Pipeline (Recommended)

The primary local helper for running the data pipeline is `run_optimized_pipeline.py`.
It mirrors the promoted daily workflow sequence for the repo-supported bands.
The canonical automation contract itself lives in
`.github/workflows/daily-pipeline.yml`.

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
# Generate live next-show predictions for a single band and model
uv run python scripts/generate_live_predictions.py --band phish --model deal

# Sync the retained last-50 completed-show prediction and metric corpus
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50

# Backfill Eggy raw tables without validation warnings
uv run python scripts/run_eggy_collection.py --skip-validation

# Convenience wrappers for Billy Strings predictions
uv run predict-billy -- --date 2025-10-24
uv run predict-billy -- --date 2025-10-24 --model deal
```

For detailed usage, please refer to the full documentation.

### Website Surface

JamBandNerd now ships a website-first product surface in `apps/web`. The target architecture is a monorepo website application with server-side reads from Supabase and production hosting on Vercel.

The target website experience includes:

- **Multi-band selection**: Switch between all dynamically discovered bands.
- **Live predictions**: One precision-optimized prediction board per band — the single best answer to "what's likely tonight?"
- **Accuracy visualization**: Historical performance charts with configurable K values (K=10/25/50; selected K highlighted).
- **Show details**: Prominent Next Show header with venue and prediction timestamp.

The primary local UI workflow is:

```bash
npm install
npx playwright install --with-deps chromium
cp apps/web/.env.local.example apps/web/.env.local
npm run dev:web
npm run verify:web
```

The website delivery path now uses Vercel’s native GitHub integration model. Treat `main` as the production branch and use preview deployments for feature branches and pull requests.

### Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Canonical verification commands
npm run verify:python
npm run verify:docs
npm run verify:web
npm run verify:all

# Final tracked-file drift check on a clean baseline
npm run verify:clean
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
  The canonical end-to-end data contract now lives in
  [Data Strategy](docs/reference/specifications/data_strategy.md).
- 📈 **[Reports](docs/reports/)**: Summaries of improvements and validation testing.

Generate and serve documentation locally:

```bash
uv pip install -e ".[docs]"
NO_MKDOCS_2_WARNING=true uv run --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs serve
```

## Architecture

**Show-Centric Pipeline Design**: Data Sources -> Raw Storage -> Shared
Normalization -> In-Memory Transform -> Models -> Predictions/Accuracy ->
Website

**Supported Bands**: Workflow support is repo-authoritative and defined in
`src/jambandnerd/config/bands.py`. The live `bands` registry in Supabase is
runtime metadata for the website and other data consumers. New bands should
follow the collector script pattern, update the repo band config, add a
`bands` row, and then validate the consolidated pipeline and website paths.

**Key Components**:

- Band-specific raw collectors with unified downstream contracts.
- Show-centric normalization of shows, setlists, and songs before modeling.
- In-memory transformation pipeline (no intermediate transformed tables).
- Single per-band prediction model, precision-optimized for top-25 setlist accuracy.
- Unified cross-band prediction and accuracy storage.
- Supabase backend with automated validation.
- Website-first product delivery through the live `apps/web` surface.
- **GitHub Actions automation** with daily pipeline execution.
- **Per-band workflow health reporting** so upstream-specific issues can degrade gracefully without masking the rest of the platform.

### Widespread Panic Data & Fallback

The WSP data collector scrapes `everydaycompanion.com`. This process is enhanced with browser automation (Playwright) to ensure high reliability even against sophisticated bot detection. If a recent historical setlist is missing from EC, the pipeline attempts a backup read from `TourWrangler.com` using a cleaned parser. When EC later publishes the setlist, the EC data will automatically replace the TourWrangler data, ensuring the highest quality data is used.

### Automation

The platform features comprehensive automation through GitHub Actions:

- **Daily Pipeline**: Runs automatically at 3 PM ET every day.
- **Fantasy Goose**: A dedicated GitHub Actions workflow can auto-submit Goose notebook picks when Fantasy Goose exposes an eligible show and the required secrets are configured.
- **Dynamic Matrix**: The pipeline runs the repo-authoritative automation band list through `scripts/get_all_bands.py`.
- **Manual Triggers**: On-demand execution with band selection via the GitHub UI.
- **Error Resilience**: Parallel matrix execution with graceful failure handling and explicit degraded-mode reporting for volatile upstreams such as WSP.
- **Secret Management**: Secure API key and database credential handling.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow overview and [docs/contributor/onboarding.md](docs/contributor/onboarding.md) for contributor-specific orientation.

## License

MIT
