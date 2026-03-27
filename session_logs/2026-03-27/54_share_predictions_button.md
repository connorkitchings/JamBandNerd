# Session Log: 2026-03-27 (Share Predictions, OG Tags, Show Exclusions, Data Wipe)

\ NoUnexpectedOutput: true

## Goal
\ NoUnexpectedOutput: true

Add share/copy button to the predictions page, add Open Graph meta tags for rich iMessage previews, refactor prediction show exclusions from date-based to show-ID-based, wipe and re-ingest all Goose data, and fix song search empty-state overlay.
\ NoUnexpectedOutput: true

## Constraints
\ NoUnexpectedOutput: true

- Must work well on mobile (primary use case: sharing with friends via iMessage)
- OG image previews only work for publicly accessible URLs (not localhost)
- Show exclusion system needed to support same-day multi-show precision (show ID vs date)

## Commands Run
\ NoUnexpectedOutput: true

```bash
npm run lint:web
npm run build:web
node --test apps/web/tests/unit/format-predictions-text.test.ts
npm run test:web:smoke
uv run ruff check src/jambandnerd/config/bands.py src/jambandnerd/config/__init__.py scripts/common.py tests/pipeline/test_normalization_contract.py scripts/wipe_band_data.py
uv run pytest tests/pipeline/test_normalization_contract.py -q
uv run python scripts/wipe_band_data.py --band goose
uv run python scripts/run_optimized_pipeline.py --band goose
```

## Files And Artifacts
\ NoUnexpectedOutput: true

### New Files
\ NoUnexpectedOutput: true

- `apps/web/src/lib/format-predictions-text.ts` -- Pure utility exporting `formatTop10Text()`.
- `apps/web/src/components/share-predictions-button.tsx` -- Client component with `navigator.share()` + clipboard fallback.
- `apps/web/tests/unit/format-predictions-text.test.ts` -- 4 unit tests.
- `scripts/wipe_band_data.py` -- Utility to wipe all band data from Supabase for clean re-ingestion.

### Modified Files
\ NoUnexpectedOutput: true

- `apps/web/src/app/predictions/page.tsx` -- Share button in Song Board header, `formatTop10Text()` call, OG metadata in `generateMetadata()`.
- `apps/web/src/app/layout.tsx` -- Added `metadataBase`, `openGraph` baseline for all pages.
- `apps/web/src/components/song-search.tsx` -- Removed "no songs match" dropdown overlay; dropdown only renders when results exist.
- `src/jambandnerd/config/bands.py` -- Added `EXCLUDED_PREDICTION_SHOW_IDS` (show-ID based exclusions for addition to date-based), 5 Goose shows excluded.
- `src/jambandnerd/config/__init__.py` -- Exported new exclusion constants.
- `scripts/common.py` -- `prepare_band_data` now merges both date and show-ID exclusions.
- `tests/pipeline/test_normalization_contract.py` -- Updated exclusion test for show-ID based exclusions.

## Data Operations
\ NoUnexpectedOutput: true

- Wiped all Goose data (599 songs, 834 shows, 586 venues, 6955 setlists, 1361 accuracy rows, 295 historical runs, 4 notebook predictions, 2 CK+ predictions)
- Re-ingested from elgoose.net API (598 songs, 833 shows, 582 venues, 6950 setlists)
- Re-ran full pipeline: 100-show backtest per model, all validations passed
- Excluded 5 Goose shows from prediction/backtest windows:
  - 1755099318 (2025-08-13 TV appearance)
  - 1748090458 (2025-05-25 Napa short set)
  - 1745685585 (2025-04-25 short set)
  - 1741108426 (2025-03-11 promo)
  - 1730168333 (2024-11-24 MSG short set)

## Validation
\ NoUnexpectedOutput: true

- ESLint: clean
- Next.js build: clean
- Python ruff: clean
- Unit tests: 3/3 pass (normalization contract), 4/4 pass (format-predictions-text), 11/11 pass (Playwright smoke)

- Full Goose pipeline: SUCCESS (42.3s)

- 0 excluded shows remain in accuracy_per_show data

## Next Step
\ NoUnexpectedOutput: true

- Create the 3-model compare canonical script (from session 53 next step)
- Add a custom OG image for predictions page (currently using logo.png)
- Consider adding the share URL with UTM params for tracking shares
