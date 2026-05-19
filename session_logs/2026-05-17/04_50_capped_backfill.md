# Session Log: 50-Capped Backfill — All Bands

Date: 2026-05-17

## Goal

Complete the 50-capped backfill of the last 50 show predictions for each band, so Top 50 metrics show real data (not clones of Top 25). Fix capability issues encountered during the run.

## Summary

### Root cause
`default_top_k` was changed from 25 → 50 in `metadata.py` (session `03`), but the existing `setlist_results` / `setlist_accuracy` data still had only 25 predictions per show. The optimized pipeline uses `incremental=True` for backtests, so a full recompute (`--no-incremental`) was needed.

### Supabase write credential issue
The `.env` had `SUPABASE_SERVICE_ROLE_KEY=''` (empty) and `SUPABASE_KEY` set to the publishable/anon key (`sb_publishable_...`). Writes to `setlist_results` failed with RLS policy violation. Fixed by setting `SUPABASE_SERVICE_ROLE_KEY` to the `sb_secret_...` key from Supabase Dashboard → Settings → API Keys.

### Pre-flight write check added
Added `_verify_supabase_write_access()` to `scripts/run_backtest.py` that runs before any model training. It checks the Supabase API key prefix — if it's `sb_publishable_...`, it raises early with a clear message instead of failing after 30+ minutes of scoring.

### Backfill results

Per-band commands:
```
uv run python scripts/run_backtest.py --band <band> --shows 50 --no-incremental
```

| Band | K=50 Precision | K=50 Recall | K=25 Precision | K=25 Recall | Dual |
|------|---------------|-------------|----------------|-------------|------|
| Goose | 0.145 | 0.591 | 0.204 | 0.415 | 0.418 |
| Phish | 0.193 | 0.540 | 0.238 | 0.335 | 0.408 |
| WSP | 0.237 | 0.583 | 0.309 | 0.380 | 0.468 |
| Billy | 0.204 | 0.411 | 0.268 | 0.266 | 0.360 |
| UM | 0.123 | 0.398 | 0.130 | 0.212 | 0.275 |

All bands now have distinct K=50 metrics (previously identical to K=25).

## Validation

- `uv run python scripts/validate_accuracy_tables.py --max-age-hours 72 --replay-window 50 --skip-freshness --require-exact-retained-window` — all 5 bands pass, exactly 50 rows each in `setlist_accuracy` and `setlist_results`
- `black --check` + `ruff check` — clean on `scripts/run_backtest.py`
- `uv run pytest -q tests/pipeline/test_run_backtest.py tests/test_validate_accuracy_tables.py` — 16 passed
- `npm run verify:web` — 10 passed, 10 skipped

## Files Changed

- `scripts/run_backtest.py` — added `_verify_supabase_write_access()` pre-flight check
- `.env` — set `SUPABASE_SERVICE_ROLE_KEY` to secret key (not committed)

## Next Step

Push `dev` with the pre-flight write check. Website Top 50 metrics should now show real data distinct from Top 25.
