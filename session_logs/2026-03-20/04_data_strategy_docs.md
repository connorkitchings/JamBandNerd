# 2026-03-20 Session Log 04

## Goal

Document a comprehensive, show-centric data strategy that aligns ingestion,
storage, normalization, prediction, and evaluation across bands before code
implementation begins.

## Key Decisions Captured

- JamBandNerd is documented as a two-stage data system:
  - source-faithful raw storage in band-specific Supabase tables
  - shared normalized in-memory contract for transforms, models, predictions,
    and backtests
- The required predictive entities are:
  - shows
  - setlists
  - songs
- Supporting entities such as venues and upcoming shows remain optional support
  tables rather than core predictive inputs.
- Canonical show sequencing is:
  - `show_date`
  - deterministic stable tiebreaker
- Current prediction storage remains canonical for now:
  - one row per `(band, reference_date, model_version)` in
    `predictions_{model}`
  - ranked JSON payload in `predictions`
- `accuracy_per_show` is the canonical granular evaluation store; aggregate
  accuracy tables are derived summaries.

## Docs Added

- `docs/reference/specifications/data_strategy.md`
- `docs/operations/streamlit_deploy.md`

## Docs Updated

- `README.md`
- `mkdocs.yaml`
- `docs/index.md`
- `docs/contributor/developer_guide/architecture.md`
- `docs/contributor/developer_guide/extending_the_platform.md`
- `docs/contributor/onboarding.md`
- `docs/user/configuration.md`
- `docs/reference/specifications/technical_overview.md`
- `docs/reference/specifications/database.md`
- `docs/reference/specifications/goose_pipeline.md`
- `docs/reference/specifications/predictions_schema.md`
- `docs/reference/schemas/unified_tables.md`

## Validation

- `uv run --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs build --strict`
  passed
- stale-reference search confirmed the edited docs no longer describe the old
  speculative prediction schema as current

## Deferred

- no code or schema implementation changes for the new strategy yet
- prediction storage migration decision remains open beyond the currently
  documented JSON-row design
- supported-band discovery is still only partially unified across automation and
  local orchestration
