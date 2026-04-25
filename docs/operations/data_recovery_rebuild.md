# Data Recovery And Derived Rebuild

This runbook covers the recommended recovery path when JamBandNerd needs schema
or normalization corrections without assuming the raw layer should be wiped.

## Default Approach

1. Audit raw tables for all bands.
2. Re-ingest only the bands that fail audit.
3. Apply schema changes.
4. Rebuild live next-show predictions and the retained completed-show corpus
   band by band.

The default assumption is:

- raw tables are the source of truth
- live prediction projections and completed-show accuracy tables are
  rebuildable outputs

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
current split live/completed prediction store, apply:

```text
supabase/migrations/20260424_split_live_and_completed_predictions.sql
```

For production safety, this schema change should be treated as a parallel-table
rollout, not an in-place mutation:

1. Create `next_show_prediction_runs`.
2. Create `next_show_prediction_songs`.
3. Create `completed_show_prediction_runs`.
4. Create `completed_show_accuracy`.
5. Keep the legacy `predictions`, `prediction_songs`,
   `historical_prediction_runs`, and `accuracy_per_show` tables untouched until
   the new tables are populated, validated, and the website cutover is complete.

Each new table must have RLS enabled immediately. Public website access should
be `SELECT` only for `anon` and `authenticated`; writes should be limited to
`service_role`.

## Rebuild Derived Outputs

Regenerate the active live board for a band/model:

```bash
uv run python scripts/generate_live_predictions.py --band goose --model notebook
```

Sync the retained last-50 completed-show corpus for all promoted models:

```bash
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --no-incremental
```

Sync all supported bands:

```bash
uv run python scripts/sync_retained_prediction_corpus.py --band all --window 50 --no-incremental
```

## Validation

After rebuild:

- rerun `scripts/audit_raw_data.py` for any band that required re-ingestion
- confirm `scripts/validate_prediction_tables.py` passes for rebuilt bands
- confirm `next_show_prediction_songs` row counts match `top_k` for the latest
  live prediction run per band/model when an upcoming show exists
- confirm `completed_show_accuracy` has exactly 50 eligible rows per promoted
  band/model
- confirm `completed_show_prediction_runs` contains the matching scored board
  for a spot-checked retained completed show
- spot-check the website performance/history surfaces for a numeric-ID band and
  a string-ID band
