# Session: Single-Model Production Promotion

**Date**: 2026-05-19
**Branch**: `dev`

## Goal

Promote the single-model-per-band release candidate toward production by
consolidating `feat/enrich-prediction-output` into `dev`, validating the active
`setlist_*` contract, and preparing `dev` for a PR into `main`.

## Work Completed

- Merged `feat/enrich-prediction-output` into `dev`.
- Aligned public version surfaces to `1.0.1`.
- Fixed Billy active band metadata to match the promoted V12 predictor:
  `billy_fast_gbm_v12_gap_scaled_p50`.
- Updated live smoke coverage to use active single-model bands and `setlist_*`
  tables instead of legacy Notebook/Deal table assertions.
- Updated retained-window tests from 100 rows to the current 50-row production
  corpus.
- Kept Eggy out of the active production live-smoke gate.

## Validation

```bash
uv run python scripts/check_version_sync.py
npm run verify:python
npm run verify:docs
npm run verify:web
```

Results:

- Version surfaces in sync: `1.0.1`.
- Python gate passed: 634 tests, including active-band live pipeline smoke for
  Goose, Phish, WSP, Billy, and UM.
- Docs gate passed.
- Web gate passed: 30 unit tests, lint, build, and 10 smoke tests passed with
  10 intentional smoke skips.

## Notes

- Running the Python gate with live environment variables present regenerated
  and validated production-style active-band data through
  `scripts/run_optimized_pipeline.py --band <band>`.
- The active write/read boundary remains the `setlist_*` table family.
- Remaining production steps: commit, push `dev`, open/update PR from `dev` to
  `main`, wait for GitHub checks and Vercel preview, then merge and run hosted
  production smoke.
