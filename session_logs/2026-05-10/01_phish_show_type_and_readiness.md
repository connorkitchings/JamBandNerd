# Phish Show-Type Experiment + Readiness Checks

## Goal

Implement the next-development plan after the five-band status review:

- Add one targeted Phish show-type signal experiment.
- Keep the incumbent registry unchanged unless the experiment clears the gate.
- Reconcile Billy baseline docs with the registered baseline.
- Verify the single-model daily matrix and website path.

## Changes

- Added `PhishFastPlusShowType` in `src/jambandnerd/models/phish/experiments.py`.
  - Extends the incumbent `PhishFastPlusNotebookRankVenueRun`.
  - Adds tour/venue/festival/atypical context features plus song-level interactions so ranking can change within a target show.
  - Registered as `PHISH_SWEEPS["show_type_sweep"]`.
- Carried `tour_name` through target show context and cleaned Phish plays so the experiment can use non-leaky show metadata.
- Updated Billy baseline docs/playbook to match code: `BillyFastBaselinePredictor` aliases `BillyFastPredictorV10` with model version `billy_fast_gbm_v10_hp_tuned`.
- Confirmed `.github/workflows/daily-pipeline.yml` still uses the active five-band matrix: `goose`, `phish`, `wsp`, `billy`, `um`; Eggy remains excluded.

## Backtest Result

Command:

```bash
uv run python scripts/run_experiment.py --band phish --sweep show_type_sweep --shows 100 --snapshot-root .snapshots/phish_phase_b
```

Result:

| Model | dual | p@10 | p@25 | r@50 | F1@25 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Incumbent baseline | 0.4186 | 0.2929 | 0.2453 | 0.5442 | 0.2831 | Keep |
| `phish_fast_gbm_v2_feat_show_type` | 0.4124 | 0.2818 | 0.2444 | 0.5430 | 0.2825 | No promotion |

The show-type interaction idea is train/predict compatible but regresses the primary dual objective and p@10. Leave it as an experiment artifact only.

## Validation

- Passed: `uv run ruff check src/jambandnerd/models/phish/experiments.py src/jambandnerd/models/phish/fast_predictor.py src/jambandnerd/transformations/run_context.py src/jambandnerd/transformations/gaps.py tests/models/test_phish_model.py`
- Passed: `uv run pytest -q tests/models/test_phish_model.py tests/models/test_model_registry.py`
- Passed after installing Playwright Chromium: `npm run verify:web`
- Fixed: `npm run verify:python` now passes after targeted Black/Ruff cleanup and
  validation fixes.
- Completed production pipeline runs:
  - Goose: live prediction, retained accuracy, prediction validation, accuracy
    validation, and per-band audit passed.
  - Phish: live prediction, retained accuracy, prediction validation, accuracy
    validation, and per-band audit passed.
  - UM: live prediction, retained accuracy, prediction validation, accuracy
    validation, and per-band audit passed after aligning UM raw collection with
    the live production schema.
- Deferred: the full five-band Supabase audit is not release-ready yet because
  WSP and Billy still cannot complete forced pipeline runs.
  - WSP is blocked by recent Everyday Companion pages with no setlist table for
    May 8 and May 9, 2026.
  - Billy is blocked by `bmfsdb.com` returning HTTP 500 during source
    reachability preflight.

## Branch Hygiene Notes

- Keep `PhishFastPlusShowType` importable as an analysis artifact only. It
  regressed the incumbent and must not be promoted.
- Keep the Billy V10 baseline docs correction; it matches the registered
  production model version.
- Keep the UM schema-sync fixes because the UM forced pipeline completed
  end-to-end against production after those changes.
- Treat `prepare_dataframe_for_upsert` dropping extra schema columns as
  intentional: validation already reports extra columns as ignored, and the
  prepared frame must match that contract before PostgREST upserts.

## Next Step

Stop cheap Phase B feature/HP sweeps for now. The highest-value next work is
branch hygiene plus upstream recovery planning: preserve the shippable
Goose/Phish/UM readiness fixes, document WSP/Billy blockers, and defer the full
five-band Supabase audit until those two upstream paths can publish current
website-facing rows.
