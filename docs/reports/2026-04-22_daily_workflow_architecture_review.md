# Daily Workflow Architecture Review

Date: 2026-04-22

## Current Daily Path

GitHub Actions YAML in `.github/workflows/daily-pipeline.yml` is the canonical
daily orchestration contract.

Per-band step order:

1. `scripts/get_all_bands.py` builds the repo-authoritative band matrix
2. `scripts/collection_preflight.py` decides collection mode and recent windows
3. `scripts/run_{band}_collection.py` performs raw ingestion
4. `scripts/verify_data_freshness.py` checks recent missing setlists
5. `scripts/generate_predictions.py` writes canonical `predictions` rows and
   `prediction_songs` projection rows for Notebook and Deal
6. `scripts/rebuild_prediction_songs.py` reconciles the bounded projection window
7. `scripts/validate_prediction_tables.py` checks canonical prediction freshness
   and projection consistency
8. `scripts/run_backtest.py` writes `historical_prediction_runs` and
   `accuracy_per_show`
9. `scripts/validate_accuracy_tables.py` checks per-show freshness and replay
   lineage
10. `scripts/check_supported_model_freshness.py` audits promoted-model freshness
11. `scripts/audit_supabase_tables.py` audits website-facing contract health
12. workflow status artifacts summarize degraded vs failed outcomes before stale
    freshness is enforced

## Canonical Storage Contract

Active derived/public-facing tables:

- `predictions`
- `prediction_songs`
- `historical_prediction_runs`
- `accuracy_per_show`

Raw ingestion remains source-faithful in `{band}_*_raw` tables and transforms
remain in memory.

## Source Of Truth Split

- Repo config in `src/jambandnerd/config/bands.py` is the authority for
  workflow-supported bands and CLI choices.
- Supabase `bands` is runtime metadata for the website and other data
  consumers.
- Runtime id-column lookup may consult `bands`, but workflow band selection
  must not vary based on Supabase reachability.

## Drifts Corrected In This Pass

- Deal daily backtest docs said `10` shows while the workflow actually runs
  `50`.
- Active docs still referred to aggregate accuracy tables even though the
  active workflow contract is `accuracy_per_show`.
- Active docs still described Phish with a legacy id column after the
  `show_id` migration.
- Active docs treated Supabase `bands` as the workflow source of truth instead
  of runtime metadata.
- `scripts/README.md` described `get_all_bands.py` as collector-file discovery
  even though it now resolves the repo-authoritative band list helper.

## Resulting Rules

- GitHub Actions YAML owns the daily workflow contract.
- Local runners may mirror the workflow, but documentation must not present
  them as the source of orchestration truth.
- Docs and tests should fail fast if active surfaces reintroduce retired table
  names, retired id-column references, or mismatched workflow window claims.
