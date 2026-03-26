# Session 27: Mobile Touch Optimization & Dynamic Band Registry

**Date:** 2026-03-26  
**Goal:** Improve mobile touch responsiveness and implement dynamic band registry

## Constraints
- Keep touch targets minimum 44px for accessibility
- Maintain thumb-first navigation ordering
- Use DB registry as single source of truth for bands

## Commands Run
```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest
```

## Files Changed

### Web UI (touch improvements)
- `apps/web/src/app/globals.css` - Added `.touch-manipulation` class and landscape media query
- `apps/web/src/app/compare/page.tsx` - Fixed apostrophe encoding, overflow handling for SongBoard
- `apps/web/src/app/replay/page.tsx` - Touch-optimized show selector links
- `apps/web/src/components/filter-links.tsx` - Applied touch-manipulation and improved touch targets
- `apps/web/src/lib/navigation.ts` - Added Home link to mobile nav
- `apps/web/tests/smoke/public-shell.spec.ts` - Updated test expectation for Home link

### Documentation
- `docs/contributor/developer_guide/architecture.md` - Added current routes, components, supported bands
- `docs/reference/specifications/database.md` - Added band registry, historical runs, prediction_songs schema
- `docs/reference/specifications/data_strategy.md` - Added bands table schema, historical prediction runs, prediction_songs schema

### Config & Pipeline
- `src/jambandnerd/config/bands.py` - Added `get_active_bands()` and `get_band_id_column()` for DB registry
- `src/jambandnerd/db/operations.py` - Added `fetch_active_bands()` function

### Scripts (refactored to use dynamic bands)
- `scripts/audit_raw_data.py`
- `scripts/generate_predictions.py`
- `scripts/get_all_bands.py`
- `scripts/rebuild_derived_data.py`
- `scripts/run_backtest.py`
- `scripts/run_optimized_pipeline.py`
- `scripts/validate_accuracy_tables.py`
- `scripts/validate_prediction_tables.py`

### Tests
- `tests/pipeline/fixtures.py` - Use dynamic bands

### Style fixes
- Various ruff/black formatting fixes across codebase

## Validation Status
All checks passed locally.

## Next Step
Test on staging to verify mobile touch responsiveness and DB registry integration