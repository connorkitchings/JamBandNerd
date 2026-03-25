# Data Recovery And Derived Rebuild

This runbook covers the recommended recovery path when JamBandNerd needs schema
or normalization corrections without assuming the raw layer should be wiped.

## Default Approach

1. Audit raw tables for all bands.
2. Re-ingest only the bands that fail audit.
3. Apply schema changes.
4. Clear and rebuild derived predictions and accuracy outputs band by band.

The default assumption is:

- raw tables are the source of truth
- prediction projections and accuracy tables are rebuildable outputs

## Audit Raw Tables

Audit all supported bands:

```bash
uv run python scripts/audit_raw_data.py --band all
```

Audit one band with verbose detail:

```bash
uv run python scripts/audit_raw_data.py --band goose --verbose
```

Use the audit to decide whether a band needs targeted raw re-ingestion.

## Apply Migration

Apply the relevant Supabase migration before rebuilding derived outputs. For the
`accuracy_per_show.show_id` alignment change and historical backtest lineage
store, apply:

```text
supabase/migrations/20260322_accuracy_per_show_show_id_text.sql
supabase/migrations/20260325_create_historical_prediction_runs.sql
```

## Rebuild Derived Outputs

Rebuild all supported bands after clearing existing derived rows:

```bash
uv run python scripts/rebuild_derived_data.py --band all --clear-existing
```

Rebuild a single band:

```bash
uv run python scripts/rebuild_derived_data.py --band goose --clear-existing
```

Rebuild only recent accuracy history:

```bash
uv run python scripts/rebuild_derived_data.py --band goose --clear-existing --recent-shows 100
```

Rebuild accuracy without regenerating predictions:

```bash
uv run python scripts/rebuild_derived_data.py --band goose --clear-existing --skip-predictions
```

## Validation

After rebuild:

- rerun `scripts/audit_raw_data.py` for any band that required re-ingestion
- confirm `scripts/validate_prediction_tables.py` passes for rebuilt bands
- confirm `prediction_songs` row counts match `top_k` for the latest prediction
  run per band/model
- confirm recent `accuracy_per_show` rows have non-null `prediction_run_id`
- confirm `historical_prediction_runs` contains the matching scored board for a
  spot-checked recent show
- spot-check the website performance/history surfaces for a numeric-ID band and
  a string-ID band
