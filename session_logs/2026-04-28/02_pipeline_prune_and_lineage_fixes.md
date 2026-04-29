# Daily Pipeline Diagnostics: Prune Cache Destruction and Lineage Fixes

## Goal

Diagnose why the daily pipeline was failing for UM and running over 30 minutes for multiple bands (goose 33 min, eggy 34 min, UM 103 min).

## Constraints

- Keep changes to backtest, validation, and lineage logic only
- Preserve existing test contracts and workflow YAML
- Do not change Deal model internals in this pass

## Root Causes Found

### 1. Prune step destroying incremental backtest cache (critical)

`scripts/run_backtest.py` line 486 used `target_shows` (filtered by incremental mode to only new shows) as the retained key set for `prune_completed_show_corpus`. After incremental mode filtered 50 shows down to 1-2 new ones, the prune step deleted the other 48-49 scored rows from the corpus. This caused an oscillating cycle: Day A scores 1 show and prunes 49; Day B must retrain Deal on ~49 shows (~30-100 min depending on band); Day C scores 1 and prunes again.

**Fix**: Save `full_window_show_ids` before the incremental filter and use that for pruning instead of the filtered `target_shows`.

### 2. Replay lineage validation too strict on count

`scripts/validate_accuracy_tables.py` line 207 used strict `count != window` equality. Bands with short sets (actual_song_count <= 2) have fewer than 50 eligible rows. The check failed even when all found rows had valid prediction_run_id links.

**Fix**: Restructured to check for broken links first. If all found eligible rows have valid links, a count shortfall below the window is an `[OK]` with explanation rather than a `[FAIL]`. Missing links still fail.

### 3. Silent exception swallowing in backtest

`scripts/run_backtest.py` lines 177-180 had bare `except: continue` that silently skipped failing shows with no logging. For goose, 2 shows were silently skipped, leaving 48/50 scored records.

**Fix**: Added warning output showing show ID, date, exception type, and message.

### 4. UM API migration invalidated incremental cache (one-time)

The April 27 UM API transition changed all show_ids from old format to new bigint IDs. The incremental backtest cache (keyed by show_id) found zero matches, forcing a full 50-show Deal retrain (103 minutes). This is a one-time cost — subsequent runs will use the new IDs for incremental lookups.

## Commands Run

- `gh run view` against runs 25059870032, 25072482881, 25073390647
- `uv run pytest tests/test_validate_accuracy_tables.py -v` — 14 passed
- `uv run pytest tests/pipeline/test_run_backtest.py -v` — 7 passed
- `uv run pytest tests/pipeline/test_sync_retained_prediction_corpus.py -v` — 3 passed
- `uv run pytest tests/test_daily_workflow_contract.py -v` — 3 passed
- `uv run ruff check` and `uv run black --check` — clean

## Files Changed

- `scripts/run_backtest.py`: Save full_window_show_ids before incremental filter; use it for prune; add logging to exception handlers
- `scripts/validate_accuracy_tables.py`: Restructure replay lineage validation — check broken links before count mismatch
- `tests/test_validate_accuracy_tables.py`: Add 3 new tests for eligible-row-below-window scenarios

## Validation Status

- All 27 tests pass (14 validate_accuracy + 7 run_backtest + 3 sync_corpus + 3 workflow_contract)
- Lint and format clean
- No docs changes needed

## Next Step

Merge to dev and dispatch a daily pipeline run for goose and UM to verify the prune fix restores incremental caching and the lineage validation passes with 48/50 eligible rows.
