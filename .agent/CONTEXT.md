# JamBandNerd Context Router

This is the startup router for AI tools. Do not treat it as a full architecture document.

## Repo Snapshot

- JamBandNerd is a Python 3.12 data platform for jam band setlist collection, transformation, prediction, and visualization.
- Core flow: sources -> collectors -> Supabase raw tables -> in-memory transforms -> models -> predictions/backtests -> website delivery surface.
- The `apps/web` website is the public product surface. Streamlit is retired and retained only in historical docs/logs.
- The recommended end-to-end entrypoint is `scripts/run_optimized_pipeline.py`.
- Active AI workflow lives under `.agent/` and `session_logs/`.
- Historical AI/dev logs remain in `docs/logs/` as archive only.

## Read Next

1. `pyproject.toml`
2. `README.md`
3. `docs/user/pipeline_usage.md`
4. `docs/contributor/developer_guide/architecture.md`

After that, load only what the task needs.

## Repo Rules That Matter Most

- Command source of truth: `README.md` and `docs/user/pipeline_usage.md`
- Anti-leakage rule: `reference_date` is mandatory in feature generation and backtesting
- In-memory transforms only: no intermediate Supabase tables
- Band-agnostic core (partial): shared transforms, `ModelData`, `PredictionModel` ABC, and storage contract stay generic; collector logic stays in `data_collection/{band}/`; per-band predictor classes are allowed in `models/{band}/` (see ADR 0001)
- Dynamic band discovery comes from `scripts/run_*_collection.py`

## Core Paths

- Source: `src/jambandnerd/`
- Pipeline scripts: `scripts/`
- Tests: `tests/`
- User docs: `docs/user/`
- Contributor docs: `docs/contributor/`
- Operations docs: `docs/operations/`
- Historical archive: `docs/logs/`
- Active session logs: `session_logs/`

## Start Session

- Check branch and avoid working on `main`
- Load one skill from `.agent/skills/CATALOG.md` if the task matches
- Check the latest file in `session_logs/` when continuity matters

## End Session

Before closing a meaningful work session:
- update `session_logs/YYYY-MM-DD/NN.md`
- capture reusable lessons in `.agent/PLAYBOOK.md`
- update docs if entrypoints, commands, or workflows changed
