# CLI Specification: jbn

This document defines the command-line interface design for JamBandNerd. The CLI is a thin wrapper
over reusable Python APIs and is designed to support a daily repeated job.

## Command Name

- `jbn` (short for "JamBandNerd").

## Design Approach

- API-first: Core orchestration implemented in Python classes/functions.
- CLI wrapper: Implemented with Typer for help, validation, and discoverability.
- Config: Optional `--config` (YAML/JSON) may be added later; not in MVP.

## Bands and Models

- Goose-first (Phase 2). Additional bands will follow.
- Table naming for predictions and accuracy is unified and includes the model identifier:
  - `predictions_{model_slug}`
  - `accuracy_{model_slug}`
  - Example: `predictions_notebook`

## Commands

### Collect

```bash
jbn collect goose [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--incremental]
```

- Purpose: Fetch raw data from source into Supabase raw tables.
- Defaults: If no dates provided, collect all available data (initial backfill).
- Notes: Goose API has no key; daily incremental collection is the normal mode.

### Transform

```bash
jbn transform goose
```

- Purpose: Transform all available raw data into standardized model-ready tables/frames.
- Dates: Not required; process all available data.

### Predict

```bash
jbn predict goose --model notebook
```

- Purpose: Generate predictions using the specified model over all applicable data.
- Dates: Not required; use all relevant data.
- Naming: Writes to `predictions_{model_slug}` and updates `accuracy_{model_slug}`.

### Run (pipeline orchestration)

```bash
jbn run goose --stages collect,transform,predict --model notebook [--since YYYY-MM-DD]
[--until YYYY-MM-DD] [--incremental]
```

- Purpose: Execute multiple stages in order. Dates apply only to collect.
- Defaults: For initial backfill, omit dates (collect all).
- Daily run: Typically `jbn run goose --stages collect,transform,predict --model notebook --incremental`.

### Run All (future)

```bash
jbn run-all --stages collect,transform,predict
```

- Purpose: Execute across all bands when they exist.
- Status: Planned for after Goose pipeline is stable.

## Global Options (Flags)

- `--log-level {DEBUG,INFO,WARNING,ERROR}`: Controls verbosity.
- `--dry-run`: Execute without writing to the database (where supported).
- `--parallel`: Enable parallel steps where safe.
- `--output {supabase,stdout,file}` (for transform/predict): Destination for results.
- Exit codes: 0 on success; non-zero for partial/critical failures.

## Scheduling (Docs-only for now)

- Goal: A repeated daily job.
- Example (cron or GitHub Actions):
  - `jbn run goose --stages collect,transform,predict --model notebook --incremental`
- Automation will be designed later; CLI is cron-friendly by default.

## Glossary

- Flag: A command-line option that modifies behavior (e.g., `--log-level INFO`).
- Model slug: A short, lowercase identifier for a model, used in naming (e.g., `notebook`, `ckplus`).
- Incremental collection: Collecting only new/changed data since the last successful run.

## Open Questions

- Add `--config` support later for complex orchestrations?
- Add `--profile` to show timing metrics?
