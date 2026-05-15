# WSP Gap Decoupling Sweep

## Goal

Test whether decoupling gap from rotation strength fixes the model's tendency to suppress core rotation songs (ranked below position 50) on failure shows. The failure analysis identified that `overdue_ratio = gap * career_pct` and `long_rotation_pressure = gap * pct100` amplify gaps for core songs, causing the model to rank them too low.

## Hypothesis

Adding `gap_percentile` (gap normalized by song's own gap distribution) and `gap_vs_median` (current gap / median gap) would let the model distinguish "unusually high gap for this song" from "song is being dropped from rotation," recovering the 50 core rotation songs ranked below position 50.

## Results

Incumbent: wsp_fast_gbm_v2 — dual=0.4484, p@10=0.3290, p@25=0.2980, r@50=0.5678, F1@25=0.3248

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | F1@25 delta | p@25 delta |
|---|---|---|---|---|---|---|---|
| gd_default | 0.440 | 0.317 | 0.290 | 0.563 | 0.316 | -0.008 | -0.008 |
| gd_fr50 | 0.440 | 0.317 | 0.290 | 0.563 | 0.316 | -0.008 | -0.008 |
| gd_clean_fr50 | 0.440 | 0.318 | 0.288 | 0.562 | 0.314 | -0.010 | -0.010 |

**Verdict: All three regress. Gap decoupling hurts performance.**

## Key Findings

1. **gd_default == gd_fr50 (identical)** — The model's early stopping converges to the same result with these features. The new features don't change the loss landscape enough to warrant different training depth.

2. **Additive features are noise** — Adding `gap_percentile` and `gap_vs_median` to the existing 19 features reduces F1@25 by 0.008. The model can't leverage the decoupled signal effectively alongside the coupled features.

3. **Removing coupled features is worse** — `gd_clean_fr50` (which removes `overdue_ratio` and `long_rotation_pressure` in favor of the decoupled versions) drops F1@25 by 0.010. The coupled features carry valuable signal that the decoupled versions don't replicate.

4. **The gap coupling hypothesis was wrong** — The failure analysis identified core songs ranked below 50 and hypothesized that gap coupling was the cause. But the coupled features `overdue_ratio = gap * career_pct` and `long_rotation_pressure = gap * pct100` are actually MORE informative than the decoupled versions. The model's problem isn't gap coupling — it's something else.

## Root Cause Reassessment

The failure analysis showed 50 core songs ranked below 50. But the gap coupling was a symptom, not the cause. The real issue appears to be:

- **Insufficient model capacity**: With ~11 boosting rounds and rank_xendcg objective, the model learns a shallow decision surface. It can't simultaneously model "predict the 20-25 songs most likely to appear" for shows with very different song distributions.
- **No set-level prediction**: The model predicts each song independently. It can't learn "this show will have an unusual set" — it just ranks songs by individual likelihood.
- **The 50 core songs ranked below 50 aren't a gap problem** — they're a candidate-ranking problem that requires deeper architectural changes, not feature tweaks.

## Decision

**No promotion. Keep wsp_fast_gbm_v2.**

The gap decoupling experiment conclusively rules out gap coupling as the cause of the failure shows. The coupled features are actually helping, not hurting.

## Artifacts

- `src/jambandnerd/models/wsp/fast_predictor.py` — added `_gap_vs_median_arr`, `WSPFastGapDecoupled`, `WSPFastGapDecoupledClean`
- `src/jambandnerd/models/wsp/experiments.py` — added `WSP_GAP_DECOUPLED_SWEEP`
- `tests/models/test_wsp_model.py` — added gap decoupled tests (31 passed)
- `backtests/wsp_wsp_fast_gbm_v2_gap_decoupled_*` — 2 experiment summaries
- `backtests/wsp_wsp_fast_gbm_v2_gap_decoupled_clean_*` — 1 experiment summary
