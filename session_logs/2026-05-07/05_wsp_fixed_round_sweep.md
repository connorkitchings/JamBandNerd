# WSP Fixed-Round Training Sweep

## Goal

Probe the 30-50 fixed-round sweet spot identified by the es_sweep. The `es_none_r50` config hit F1@25=0.3292 (+0.004), suggesting the model benefits from more boosting depth but overfits beyond 50 rounds. This sweep tests round counts 30-50 with lr=0.03 (default) and lr=0.05 (higher per-round learning), with and without regularization.

## Results

Incumbent: wsp_fast_gbm_v2 — dual=0.4484, p@10=0.3290, p@25=0.2980, r@50=0.5678, F1@25=0.3248

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | F1@25 delta | p@25 delta |
|---|---|---|---|---|---|---|---|
| fr_r30 | 0.451 | 0.330 | 0.300 | 0.571 | 0.327 | +0.002 | +0.002 |
| fr_r40 | 0.452 | 0.330 | 0.296 | 0.573 | 0.323 | -0.002 | -0.002 |
| fr_r50 | 0.451 | 0.330 | 0.302 | 0.572 | 0.329 | +0.004 | +0.004 |
| fr_r40_lr05 | 0.448 | 0.323 | 0.288 | 0.573 | 0.314 | -0.011 | -0.010 |
| fr_r50_lr05 | 0.447 | 0.321 | 0.290 | 0.573 | 0.315 | -0.009 | -0.008 |
| fr_r40_lr05_lam01 | 0.448 | 0.325 | 0.301 | 0.571 | 0.328 | +0.003 | +0.003 |
| fr_r50_lr05_lam01 | 0.448 | 0.324 | 0.300 | 0.571 | 0.327 | +0.002 | +0.002 |

**Promotion rule**: F1@25 >= 0.3298 (+0.005) AND p@25 >= 0.2960.

**Verdict**: No challenger clears the F1@25 bar. `fr_r50` confirms the es_none_r50 result at F1@25=0.3292 (off by 0.0006).

## Key Findings

1. **lr=0.03 + 50 fixed rounds remains the strongest config** (F1@25=0.3292, dual=0.451). This is reproducible — confirmed across two separate sweep runs.

2. **lr=0.05 is strictly worse for fixed-round WSP training.** Both fr_r40_lr05 (0.314) and fr_r50_lr05 (0.315) significantly degraded. The higher learning rate overfits faster in the fixed-round regime.

3. **lr=0.05 + lambda=0.1 partially recovers** (fr_r40_lr05_lam01: F1@25=0.328) but still trails lr=0.03 at 50 rounds. Regularization helps but can't overcome the wrong learning rate.

4. **The performance plateau is real.** Across all 4 sweeps (combo, es, and now fixed_round), the best WSP V2 F1@25 result is 0.3292. The model architecture and feature set appear to be at ceiling for this evaluation window.

## Decision

**No promotion. Keep wsp_fast_gbm_v2.**

This concludes the WSP V2 training procedure exploration. The findings are clear:
- The incumbent's early stopping is suboptimal (~11 rounds) but the model's ceiling with fixed rounds is only +0.004 F1@25 better
- lr=0.03 is the correct learning rate; lr=0.05 degrades regardless of regularization
- No cheap HP or training procedure change can clear the +0.005 F1@25 promotion bar

**WSP V2 is at ceiling.** Future WSP improvements require:
1. Per-show failure analysis on the bottom 12% (Experiment 2 from the diagnostics plan)
2. New features or a different model architecture (set-level prediction, multi-label, etc.)
3. Candidate generation changes

## Artifacts

- src/jambandnerd/models/wsp/experiments.py — added WSP_FIXED_ROUND_SWEEP + fixed_round_sweep
- tests/models/test_wsp_model.py — updated sweep registration + fixed_round_sweep tests (31 passed)
- backtests/wsp_wsp_fast_gbm_v2_fr_*_summary.json — 7 experiment summaries
