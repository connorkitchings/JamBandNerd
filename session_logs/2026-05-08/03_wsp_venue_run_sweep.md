# WSP Venue Run Sweep

## Goal

Test whether same-venue run features help the model predict multi-night run setlists. 10/12 failure shows are multi-night runs with prior shows at the same venue. WSP varies setlists across run nights, so songs played on night 1 are less likely on night 2 — this is signal the model should exploit.

`WSPFastVenueRun` (already implemented) adds 3 features: `same_venue_run_prior_played`, `same_venue_run_prior_play_count`, `same_venue_run_prior_play_share`.

## Results

Incumbent: wsp_fast_gbm_v2 — dual=0.4484, p@10=0.3290, p@25=0.2980, r@50=0.5678, F1@25=0.3248

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | F1@25 delta | p@25 delta |
|---|---|---|---|---|---|---|---|
| vr_default | 0.444 | 0.324 | 0.300 | 0.564 | 0.327 | +0.002 | +0.002 |
| vr_fr50 | 0.444 | 0.324 | 0.300 | 0.564 | 0.327 | +0.002 | +0.002 |
| vr_fr50_lam01 | 0.444 | 0.324 | 0.300 | 0.564 | 0.327 | +0.002 | +0.002 |

**Verdict: No promotion. F1@25 gains +0.002 but dual drops -0.004 (p@10 regresses -0.005).**

## Key Findings

1. **All three configs produce identical results.** The venue-run features have zero effect on training dynamics — early stopping, fixed 50 rounds, and regularization all converge to the same model. The features are being completely ignored.

2. **Why they're ignored**: The venue-run features are non-zero only for shows in a same-venue multi-night run. For the ~70% of training rows that are NOT run shows, these features are all zeros. With ~11 boosting rounds, the model can't afford to split on features that are mostly zero — it focuses on universally informative features (gap_shows, long_rotation_pressure, career_play_pct).

3. **Marginal F1@25 improvement (+0.002) comes from the 3 extra features adding noise to the feature space**, slightly perturbing the tree splits. It's not a meaningful signal.

4. **The dual score regression (-0.004) confirms this is not a promotion candidate.** p@10 dropped from 0.329 to 0.324, meaning the model's top-10 predictions got slightly worse.

## Root Cause

The fundamental problem is **feature sparsity**. Venue-run features are non-zero for a minority of training rows. In a ranking objective with limited boosting rounds, the model optimizes for universally applicable splits. Sparse features only help when the model has enough depth to create specialized branches (e.g., "IF same_venue_run_prior_played > 0 THEN..."). With 11 rounds, this depth isn't available.

## Decision

**No promotion. Keep wsp_fast_gbm_v2.**

This is the third consecutive negative result (gap decoupling, gap decoupled clean, venue run). Combined with the combo, ES, and fixed-round sweeps, the evidence is overwhelming: the WSP V2 model is at ceiling for feature-level and HP-level improvements within the current architecture.

## Artifacts

- `src/jambandnerd/models/wsp/experiments.py` — added `WSP_VENUE_RUN_SWEEP`
- `tests/models/test_wsp_model.py` — updated sweep registration tests (33 passed)
- `backtests/wsp_wsp_fast_gbm_v2_feat_venue_run_*` — experiment summaries
