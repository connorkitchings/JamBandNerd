# Data Recovery And Derived Rebuild

> **Branch note (feat/single-model-per-band)**: This runbook describes recovery
> procedures for the **legacy multi-model storage** (`next_show_prediction_runs`,
> `completed_show_prediction_runs`, `predictions`, etc.) which remains active on
> `main`/`dev`. Once the single-model-per-band architecture is cut over, this
> runbook will be updated to reference the new `setlist_*` tables and the
> simplified (no `--model` flag) pipeline scripts.

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

Before writing any new split-storage rows, run the rollout checker in empty
mode. This confirms the parallel tables are readable and still unpopulated:

```bash
uv run python scripts/check_prediction_storage_rollout.py --band goose --expected-state empty
```

Use dry runs to rehearse the Goose payloads without mutating Supabase:

```bash
uv run python scripts/generate_live_predictions.py --band goose --model notebook --dry-run
uv run python scripts/generate_live_predictions.py --band goose --model deal --dry-run
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model notebook --dry-run --no-incremental
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model deal --dry-run --no-incremental
```

The retained-corpus command emits one progress line per scored show. This is
especially important for Deal, which performs fresh in-memory training during
historical scoring and can run much longer than Notebook.

Regenerate the active live board for a band/model:

```bash
uv run python scripts/generate_live_predictions.py --band goose --model notebook
```

Sync the retained last-50 completed-show corpus for all promoted models:

```bash
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --no-incremental
```

For a first-band rollout, prefer model-by-model writes so a slow Deal run is
observable and independently retryable:

```bash
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model notebook --no-incremental
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model deal --no-incremental
```

Sync all supported bands:

```bash
uv run python scripts/sync_retained_prediction_corpus.py --band all --window 50 --no-incremental
```

## Validation

After rebuild:

- rerun `scripts/audit_raw_data.py` for any band that required re-ingestion
- confirm `scripts/check_prediction_storage_rollout.py --band goose --expected-state populated` passes for rebuilt bands
- confirm `scripts/validate_prediction_tables.py` passes for rebuilt bands
- confirm `next_show_prediction_songs` row counts match `top_k` for the latest
  live prediction run per band/model when an upcoming show exists
- confirm `completed_show_accuracy` has exactly 50 eligible rows per promoted
  band/model
- confirm `completed_show_prediction_runs` contains the matching scored board
  for a spot-checked retained completed show
- spot-check the website performance/history surfaces for a numeric-ID band and
  a string-ID band
