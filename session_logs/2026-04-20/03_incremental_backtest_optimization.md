# Session 03 — Incremental Backtest Optimization

## Goal

Review the backtesting and history backfilling pipeline for efficiency. The backtest step was taking too long; goal was to understand why and fix it without changing what the website serves.

## Constraints

- Website contract: last 50 shows per band/model from `accuracy_per_show` and `historical_prediction_runs`
- `reference_date` anti-leakage must be preserved (untouched)
- No intermediate Supabase tables; in-memory transforms only
- All existing escape hatches (`--all-history`, `--no-incremental`) must remain functional

## Root Cause

The pipeline was recomputing 600 backtest iterations per CI run (6 bands × 2 models × 50 shows) even though:
- Completed show accuracy scores are **immutable** once written
- The website only queries the most recent 50 rows
- Typical daily cadence produces 0–2 new shows per band

For the Deal model this meant 20,000 epochs of logistic regression gradient descent per band per day, for results that were already in the database.

## Changes

| File | Change |
|------|--------|
| `src/jambandnerd/db/operations.py` | Added `fetch_scored_show_ids()` — batched IN query against `accuracy_per_show` |
| `scripts/run_backtest.py` | Added `incremental: bool = True` param + `--incremental`/`--no-incremental` CLI flag; filters target shows to only unscored ones after window selection |
| `scripts/run_optimized_pipeline.py` | `shows=100` → `shows=50`; explicit `incremental=True` |
| `.github/workflows/daily-pipeline.yml` | Both models: `--incremental` added; Deal `--shows 10` → `--shows 50` |
| `docs/user/pipeline_usage.md` | Documented incremental mode and `--no-incremental` override |
| `tests/pipeline/test_run_optimized_pipeline.py` | Updated expected kwargs to match new `shows=50` + `incremental=True` |

## Key Design Decisions

- Empty window (no shows found) still raises under `--require-results` — guards against data loading failures
- "All already scored" returns 0 cleanly without raising — valid steady state
- `--all-history` bypasses incremental filter (full recompute semantics implied)
- First CI run after merge will be a one-time catch-up for Deal (0→50 shows); subsequent runs are 0–2 shows

## Validation

- `uv run ruff check` — all checks passed
- `uv run python -m pytest tests/ -x -q` — 317 passed, 6 skipped
- Import smoke test: `from scripts.run_backtest import run_backtest; from src.jambandnerd.db.operations import fetch_scored_show_ids` — ok

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Daily CI iterations | 600 | ~12–24 (days with shows), ~0 (off days) |
| Deal training epochs/band | 20,000 | ~800 (1–2 new shows) |
| Supabase writes/run | ~1,200 rows | ~24 rows |

## Actual CI Results (run 24686325598, 2026-04-20)

All 6 bands ran successfully in 8m26s wall-clock.

**Incremental output per band/model:**
- Eggy, Billy, WSP, Phish, UM: 50/50 already scored, 0 new — instant
- Goose/Deal: 49 already scored, **1 new** (April 19 show) — scored correctly

**WSP step timing (slowest band at 7m53s):**
| Step | Duration |
|------|----------|
| Setup + Playwright install | ~60s |
| Collection (Playwright browser) | 2m59s |
| Prediction generation (Deal ×2 dates) | **3m37s** |
| Run Backtest (both models, 0 new) | **7s** |
| Validation/audit | ~30s |

Backtest is no longer in the critical path. **Deal prediction generation** is now the dominant compute cost — trains from scratch for 2 reference dates per band per run. The two dates are typically 1–2 days apart with nearly identical training data.

## Performance Opportunities Remaining

1. **Deal prediction generation (primary)**: Two training runs per band per day (~1m45s each for large bands). Options: warm-start second training from first run's weights, or detect when both reference dates share the same completed-show list and reuse predictions.
2. **Playwright collection** (WSP/Eggy): Infrastructure constraint, hard to optimize further.
3. The 8m26s wall-clock is already fast for a 6-band parallel run. May not need further optimization unless CI minutes become a concern.

## Next Step

Monitor future runs to confirm the 0-new pattern holds on off-days and 1–2 shows score correctly on show days. If Deal prediction generation time grows, revisit artifact reuse between adjacent reference dates in `generate_predictions.py`.
