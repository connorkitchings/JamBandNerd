# WSP Early Stopping Sweep

## Goal

Test whether fixing the WSP model's severe under-boosting (avg 11 rounds out of 700) improves F1@25. The diagnostic session (03_wsp_diagnostics.md) found that early stopping kills training almost immediately due to a small validation set (20 shows) and aggressive patience (25). This sweep tests early stopping configurations and fixed-round alternatives.

## Infrastructure Changes

- Added `attr_overrides: dict[str, Any]` to `ExperimentConfig` for arbitrary class attribute overrides
- Extended `make_experiment_predictor` to apply `attr_overrides` to ephemeral subclasses
- Updated `scripts/run_experiment.py` to pass `attr_overrides` through
- Fixed pre-existing broken imports in `phish/experiments.py` (PhishFastPredictorV3 had missing `_LGB_PARAMS`, `lgb`, `_tour_position`, `_run_position` imports)

## Results

Incumbent: wsp_fast_gbm_v2 — dual=0.4484, p@10=0.3290, p@25=0.2980, r@50=0.5678, F1@25=0.3248

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | F1@25 delta | p@25 delta |
|---|---|---|---|---|---|---|---|
| es_patience50 | 0.451 | 0.331 | 0.298 | 0.571 | 0.324 | -0.001 | +0.000 |
| es_val10 | 0.446 | 0.328 | 0.297 | 0.564 | 0.323 | -0.002 | -0.001 |
| es_val10_pat50 | 0.446 | 0.328 | 0.296 | 0.564 | 0.323 | -0.002 | -0.002 |
| es_none_r50 | 0.451 | 0.330 | 0.302 | 0.572 | 0.329 | +0.004 | +0.004 |
| es_none_r100 | 0.442 | 0.319 | 0.297 | 0.565 | 0.323 | -0.002 | -0.001 |
| es_none_r200 | 0.441 | 0.317 | 0.296 | 0.566 | 0.323 | -0.002 | -0.002 |

**Promotion rule**: F1@25 >= 0.3298 (+0.005) AND p@25 >= 0.2960.

**Verdict**: No challenger clears the F1@25 bar.

## Key Findings

1. **es_none_r50 was the strongest challenger** (F1@25=0.3292, off by 0.0006). It also had the best dual=0.451, p@25=0.302, r@50=0.572. This confirms the model benefits from slightly more boosting depth (~50 rounds vs avg 11), but the gains plateau quickly.

2. **More rounds hurt**: r100 and r200 both degraded. The model overfits beyond ~50 rounds at lr=0.03. The early stopping was doing its job — just too aggressively.

3. **Early stopping tweaks didn't help**: Increasing patience to 50 or reducing validation fraction to 10% produced negligible changes. The model converges very quickly on WSP data.

4. **The sweet spot is ~50 fixed rounds**: Better than the incumbent's ~11 avg, but 100+ causes overfitting. This suggests the model could benefit from a tuned fixed-round configuration rather than early stopping.

## Decision: No promotion, plan follow-up

Per our agreement, no promotion even though es_none_r50 came close. The findings point to a follow-up:
- Test a narrow sweep around 30-60 fixed rounds (no early stopping) combined with slight regularization
- Consider whether lr=0.03 is the right rate for 50-round training (may want lr=0.05 for fixed rounds)
- This would be a proper training procedure change, not a sweep finding

## Artifacts

- src/jambandnerd/models/experiment.py — added attr_overrides support
- src/jambandnerd/models/wsp/experiments.py — added es_sweep
- scripts/run_experiment.py — passes attr_overrides
- tests/models/test_wsp_model.py — es_sweep + attr_overrides tests (30 passed)
- src/jambandnerd/models/phish/experiments.py — fixed broken imports (pre-existing)
- backtests/wsp_wsp_fast_gbm_v2_es_*_summary.json — 6 experiment summaries
