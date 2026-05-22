# Session 02 — Shared Fast-Predictor Module Extraction

## Goal

Extract ~300 lines of duplicated matrix-feature helpers from 5 band-specific `fast_predictor.py` / `features.py` files into a shared `models/shared/matrix_features.py` module.

## Constraints

- Preserve all external import paths: WSP and UM import `_window_plays`, `_run_position`, `_tour_position`, etc. from phish — phish must re-export under the same private names.
- Two different `_run_position`/`_tour_position` algorithms exist: proximity-to-target (phish) vs pairwise-continuity (goose/billy). Keep them separate.
- Goose's `_clean_plays` coerces set types (`coerce_set_types=True`); phish/billy don't. Parameterize in shared module.
- Goose's `_build_current_gap_matrix` is zero-based; phish/billy's is one-based. Parameterize via `zero_based` flag in `build_gap_matrix`.
- 220 model tests must pass unchanged.

## Commands Run

```bash
uv run ruff check src/jambandnerd/
uv run black --check src/jambandnerd/
uv run pytest tests/models/ -x -q --tb=short
```

## Files And Artifacts

- `src/jambandnerd/models/shared/__init__.py` — new package init
- `src/jambandnerd/models/shared/matrix_features.py` — new shared module (clean_plays, build_presence, build_gap_matrix, window_plays, window_plays_by_days, build_month_cums, precompute_gap_distributions, precompute_first_play_col, precompute_avg_days_between_plays, run_position_continuous, tour_position_continuous)
- `src/jambandnerd/models/phish/fast_predictor.py` — replaced 9 local helpers with imports + re-exports
- `src/jambandnerd/models/billy/fast_predictor.py` — replaced 9 local helpers with imports + re-exports
- `src/jambandnerd/models/billy/features.py` — replaced local `_run_position`/`_tour_position` with imports from shared
- `src/jambandnerd/models/goose/fast_predictor.py` — replaced 6 local helpers with imports + wrappers for goose-specific behavior
- `src/jambandnerd/models/goose/features.py` — replaced local `_run_position`/`_tour_position` with imports from shared
- `src/jambandnerd/models/wsp/fast_predictor.py` — no changes (already imports from phish)
- `src/jambandnerd/models/um/fast_predictor.py` — no changes (already imports from phish)

## Validation

- ruff: All checks passed
- black: 107 files unchanged
- pytest tests/models/: 220/220 passed (43.39s)
- Full test suite was in progress at 58% when the previous session timed out; model tests are the relevant validation set for this refactor

## Next Step

Frontend dedup: extract `getLatestPredictionModelVersion` to `data/model-version.ts`, deduplicate venue extractors between `next-show.ts` and `parsers.ts`, extract shared loading/error skeleton components.
