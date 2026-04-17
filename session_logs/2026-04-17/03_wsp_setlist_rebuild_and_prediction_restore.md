# Session Log - 2026-04-17 / 03

## Goal

- Rebuild all WSP setlist data (corrupted by old parser comma-title bug), then regenerate prediction history and accuracy metrics from corrected data.

## Constraints

- Process in 5-year chunks for setlist repair to avoid multi-hour runs and EC rate limiting.
- Use repair script (`scripts/admin/repair_wsp_setlists_range.py`) to delete corrupted rows, then rebuild with `scripts/run_wsp_collection.py`.
- Use local snapshots (`.snapshots/wsp/`) for backtests and backfills to avoid re-downloading 62k+ rows from Supabase per prediction.
- Deal backtests limited to `--shows 50` due to per-show retraining cost (~5+ min each).

## Commands Run

```bash
# Setlist repair (8 windows, each: dry-run → delete → rebuild)
uv run python scripts/admin/repair_wsp_setlists_range.py --band wsp --from 1986-01-01 --to 1989-12-31 --dry-run
uv run python scripts/admin/repair_wsp_setlists_range.py --band wsp --from 1986-01-01 --to 1989-12-31
uv run python scripts/run_wsp_collection.py --band wsp --from 1986-01-01 --to 1989-12-31
# (repeated for 1990-1994, 1995-1999, 2000-2004, 2005-2009, 2010-2014, 2015-2019, 2020-2026)

# Local snapshots
uv run python scripts/export_backtest_snapshots.py --band wsp

# Backfill predictions with local snapshots
uv run python scripts/backfill_predictions.py --band wsp --snapshot-root .snapshots/wsp

# Backtests
uv run python scripts/run_backtest.py --band wsp --model notebook --snapshot-root .snapshots/wsp
uv run python scripts/run_backtest.py --band wsp --model deal --shows 50 --snapshot-root .snapshots/wsp

# Projection rebuild
uv run python scripts/rebuild_prediction_songs.py --band wsp

# Validation
uv run python scripts/validate_prediction_tables.py --band wsp

# Quality gates
npm run verify:python
npm run verify:docs
```

## Files Changed

- `src/jambandnerd/data_collection/wsp/parser.py` — Rewritten structured EC parser with comma-title protection
- `src/jambandnerd/data_collection/wsp/collector.py` — Added sanity gate for fragmented comma-title fallback
- `scripts/admin/repair_wsp_setlists_range.py` — New repair utility for deleting setlist rows by date range
- `scripts/backfill_predictions.py` — Added `--snapshot-root` support for local snapshot data loading
- `tests/data_collection/wsp/test_wsp_html_parsing.py` — Regression tests for comma-title handling
- `tests/data_collection/wsp/fixtures/setlist_page_with_comma_title.html` — Test fixture
- `tests/data_collection/wsp/fixtures/setlist_table_rows_with_comma_title.html` — Test fixture
- `scripts/README.md` — Documented `--snapshot-root` on backfill script
- `.agent/PLAYBOOK.md` — Added local-snapshot backfill lesson

## Artifacts Produced

- `.snapshots/wsp/` — Local snapshot directory (3,265 shows, 62,852 setlist rows)
- `accuracy_per_show` — 3,113 Notebook shows + 50 Deal shows scored
- `prediction_songs` — Rebuilt projection (50 Notebook + 50 Deal songs)

## Validation

- `npm run verify:python`: 312 tests passed, 6 skipped (live-band smoke — require env vars)
- `npm run verify:docs`: mkdocs build succeeded (warnings are pre-existing orphaned pages)
- `validate_prediction_tables.py`: predictions present and fresh; 3 "stale" warnings are false positives from 1h window

## Next Step

- Push `pr-audit-supabase` for review. CI daily pipeline will organically expand Deal accuracy history (25 shows/night). The Deal backfill staleness-loop heuristic could be improved in a follow-up but is not blocking.
