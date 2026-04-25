# Goose Split Storage Rollout

## Goal

- Populate Goose as the first production band on the split live/completed
  prediction storage architecture.

## Constraints

- Preserve legacy prediction tables during the parallel-table rollout.
- Keep other bands empty on the new split-storage architecture until Goose is
  validated.
- Commit rollout tooling before production Supabase writes.
- Run retained-history writes model by model so a slow Deal run can be retried
  independently.

## Commands Run

```bash
git commit -m "chore: harden split prediction rollout"
uv run python scripts/check_prediction_storage_rollout.py --band goose --expected-state empty
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model notebook --dry-run --no-incremental
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model deal --dry-run --no-incremental
uv run python scripts/generate_live_predictions.py --band goose --model notebook --dry-run
uv run python scripts/generate_live_predictions.py --band goose --model deal --dry-run
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model notebook --no-incremental
uv run python scripts/sync_retained_prediction_corpus.py --band goose --window 50 --model deal --no-incremental
uv run python scripts/generate_live_predictions.py --band goose --model notebook
uv run python scripts/generate_live_predictions.py --band goose --model deal
uv run python scripts/check_prediction_storage_rollout.py --band goose --expected-state populated
uv run python scripts/validate_prediction_tables.py --band goose
uv run python scripts/validate_accuracy_tables.py --band goose --skip-freshness
uv run python scripts/audit_supabase_tables.py --band goose --skip-accuracy --output /tmp/jbn_goose_populated_audit.json
```

## Result

- Goose split-storage population succeeded for promoted models:
  - `notebook_v1`
  - `deal_v2`
- Live next-show rows target `2026-04-25` / `1762797186`.
- Both live boards wrote 50 projected songs with top song `Give It Time`.
- Retained completed-show corpus wrote 50 completed-show runs and 50 accuracy
  rows per model for `2025-06-07` through `2026-04-23`.

## Files And Artifacts

- Commit `d53810e`: rollout hardening, dry-run support, model-scoped retained
  corpus sync, progress output, tests, and docs.
- Commit `c92764f`: Goose rollout session log.
- Audit artifact: `/tmp/jbn_goose_populated_audit.json`.
- New Supabase rows:
  - `next_show_prediction_runs`: 2 Goose rows
  - `next_show_prediction_songs`: 100 Goose rows
  - `completed_show_prediction_runs`: 100 Goose rows
  - `completed_show_accuracy`: 100 Goose rows

## Validation

- `check_prediction_storage_rollout.py --expected-state populated` returned
  `warning`, not `failed`, with expected Goose counts:
  - live runs: 1 per model
  - live song projection rows: 50 per model
  - completed-show runs: 50 per model
  - completed-show accuracy rows: 50 per model
- `validate_prediction_tables.py --band goose` passed.
- `validate_accuracy_tables.py --band goose --skip-freshness` passed.
- `audit_supabase_tables.py --band goose --skip-accuracy` returned one raw-data
  warning and no blockers.

## Open Warning

- Goose raw-data audit reports one recent completed show missing a setlist:
  - `show_id=1762797185`
  - audit window `2026-04-18` through `2026-04-24`
- This does not block the split-storage rollout because Replay and accuracy have
  50 retained eligible lineaged rows for both promoted models.

## Next Step

- Decide whether to remediate the missing recent Goose setlist before expanding
  the split-storage rollout to another band.
