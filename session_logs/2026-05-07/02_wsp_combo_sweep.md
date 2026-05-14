# WSP combo_sweep Experiment Pass

## Goal

Run a narrow WSP follow-up pass testing regularization combos against the promoted WSP V2 model (wsp_fast_gbm_v2). Determine whether any cheap HP combination improves F1@25 by >= +0.005 without regressing p@25 by more than -0.002.

## Constraints

- No Supabase writes.
- 100-show evaluation window from .snapshots/wsp.
- Keep wsp_fast_gbm_v2 unless the F1@25-centered promotion rule is clearly beaten.
- No new permanent predictor classes; use base_predictor_path + make_experiment_predictor.
- No retesting candidate pruning, venue_run, notebook_rank, or plays_past_year.

## Commands Run

```bash
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --only combo_v2_lambda01 --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --only combo_v2_minleaf10 --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --only combo_v2_minleaf20 --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --only combo_v2_leaves15 --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --only combo_v2_lambda01_minleaf10 --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --only combo_v2_lambda01_leaves15 --shows 100 --snapshot-root .snapshots/wsp
```

## Results

Incumbent: wsp_fast_gbm_v2 — dual=0.4484, p@10=0.3290, p@25=0.2980, r@50=0.5678, F1@25=0.3248

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | F1@25 delta | p@25 delta |
|---|---|---|---|---|---|---|---|
| combo_v2_lambda01 | 0.446 | 0.332 | 0.300 | 0.561 | 0.327 | +0.0022 | +0.002 |
| combo_v2_minleaf10 | 0.445 | 0.327 | 0.294 | 0.564 | 0.321 | -0.0038 | -0.004 |
| combo_v2_minleaf20 | 0.444 | 0.324 | 0.296 | 0.565 | 0.322 | -0.0028 | -0.002 |
| combo_v2_leaves15 | 0.449 | 0.334 | 0.300 | 0.563 | 0.327 | +0.0022 | +0.002 |
| combo_v2_lambda01_minleaf10 | 0.443 | 0.324 | 0.299 | 0.561 | 0.326 | +0.0012 | +0.001 |
| combo_v2_lambda01_leaves15 | 0.444 | 0.328 | 0.302 | 0.560 | 0.329 | +0.0042 | +0.004 |

**Verdict**: No challenger clears F1@25 >= 0.3298. Closest was combo_v2_lambda01_leaves15 at F1@25=0.3293 (off by 0.0005). wsp_fast_gbm_v2 remains promoted. WSP cheap-combo exploration is complete.

## Files And Artifacts

- src/jambandnerd/models/wsp/experiments.py — added WSP_COMBO_SWEEP + combo_sweep registration
- tests/models/test_wsp_model.py — added combo_sweep registration test + base_predictor_path coverage
- backtests/wsp_wsp_fast_gbm_v2_combo_v2_*_summary.json — per-experiment summaries (6 files)
- backtests/wsp_wsp_fast_gbm_v2_combo_v2_*_100shows.jsonl — per-show metrics (6 files)

## Validation

```bash
uv run ruff check src/jambandnerd/models/wsp/experiments.py tests/models/test_wsp_model.py  # All checks passed
uv run pytest tests/models/test_wsp_model.py tests/models/test_model_registry.py -q         # 27 passed
```

## Next Step

WSP cheap-combo exploration is complete. Future WSP work should shift to diagnostics or a larger architecture change. The combo_sweep configs remain registered in experiments.py for reference.
