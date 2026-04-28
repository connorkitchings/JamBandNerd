# 03 — WSP Song Name Canonicalization

## Goal

Fix inconsistent WSP song names across data sources (EC, PanicStream, TourWrangler) where punctuation variants like "C Brown" / "C. Brown" and "Mr Soul" / "Mr. Soul" were stored as separate songs, corrupting gap calculations and predictions.

## Constraints

- Canonical names come from the Everyday Companion song catalog (songcode.asp)
- Canonicalization must happen at the normalizer layer (single point for all sources)
- One-time DB cleanup must be an admin script, not part of the pipeline
- Unknown songs must pass through unchanged (don't block new songs)

## Commands Run

```bash
npm run verify:python          # 384 passed, 6 skipped
uv run python scripts/admin/fix_wsp_song_names.py --dry-run   # audited 62,896 rows
uv run python scripts/admin/fix_wsp_song_names.py             # fixed 2 rows (C Brown, Mr Soul)
uv run python scripts/generate_predictions.py --band wsp --model notebook --date 2026-04-18
uv run python scripts/generate_predictions.py --band wsp --model deal --date 2026-04-18
uv run python scripts/generate_live_predictions.py --band wsp --model notebook
uv run python scripts/generate_live_predictions.py --band wsp --model deal
uv run python scripts/generate_predictions.py --band wsp --model notebook --date 2026-04-30
```

## Files Changed

### New
- `src/jambandnerd/data_collection/wsp/song_canonicalizer.py` — hybrid canonicalizer (70+ static aliases + dynamic DB lookup)
- `scripts/admin/fix_wsp_song_names.py` — one-time admin cleanup script
- `tests/data_collection/wsp/test_song_canonicalizer.py` — 27 test cases

### Modified
- `src/jambandnerd/data_collection/wsp/normalizer.py` — `normalize_songs()` fixed field mapping (code/song_name); `normalize_setlists()` now canonicalizes every song_name
- `src/jambandnerd/data_collection/wsp/orchestration.py` — builds canonical lookup from DB, passes to normalizer and fallback path; fixed conflict_columns from api_song_id to song_code
- `src/jambandnerd/data_collection/wsp/panicstream.py` — removed duplicated alias logic from _normalize_song_name()
- `src/jambandnerd/data_collection/wsp/tourwrangler.py` — removed duplicated alias logic from _normalize_song_name()
- `tests/data_collection/test_wsp_normalization.py` — fixed song test data; added 6 canonicalization tests
- `tests/data_collection/wsp/test_panicstream.py` — updated raw parser expectations
- `tests/pipeline/test_band_collection_regressions.py` — updated mock signature for normalize_setlists

## Validation

- `npm run verify:python`: 384 passed, 6 skipped, 0 failed
- DB audit: 62,896 setlist rows, 718 distinct names, 0 mismatches after fix
- Predictions for 2026-04-18 and 2026-04-30 regenerated with correct gap data
- Notebook model correctly excludes recently played C. Brown and Mr. Soul
- Deal model includes them at low probability (rank 28/38)

## Bugs Found and Fixed

1. `normalize_songs()` was mapping `id`/`name` fields (API format) instead of `code`/`song_name` (EC collector format) — songs may not have been persisting correctly
2. `conflict_columns` was `["api_song_id"]` (column doesn't exist in schema) — changed to `["song_code"]`
3. Static alias `"i'm not alone": "Alone"` was wrong — EC canonical is "I'm Not Alone"
4. Static aliases `"sleepy monkey": "Monkey"` was backwards — EC canonical is "Sleepy Monkey"

## Next Step

Run the optimized pipeline for WSP (`uv run python scripts/run_optimized_pipeline.py --band wsp`) to validate that the full collection-to-prediction flow works end-to-end with canonicalization active. Monitor for any new song name variants from PanicStream/TourWrangler fallbacks.
