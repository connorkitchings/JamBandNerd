# Session 04 — Phish Combo Sweep (Final Cheap Pass)

**Date**: 2026-05-07
**Branch**: `feat/single-model-per-band`

## Goal

Run final cheap Phish pass: test whether HP tuning on the promoted stacked feature model (`PhishFastPlusNotebookRankVenueRun`) improves over V2's HP defaults. This is the last cheap Phish experiment before shifting to diagnostics or larger architecture changes.

## Constraints

- Use `uv run` for all commands
- 100-show walk-forward backtest
- Promotion threshold: dual ≥ 0.4236 (+0.005 over incumbent 0.4186)
- p@10 no meaningful regression (qualitative, current incumbent p@10=0.2929)
- No Supabase writes — snapshot-only evaluation

## Current Incumbent

```
Class: PhishFastPlusNotebookRankVenueRun
Version: phish_fast_gbm_v2_feat_notebook_rank_venue_run
Metrics (100-show): dual=0.4186, p@10=0.2929, p@25=0.2453, r@50=0.5442, F1@25=0.2831
```

## Implementation

### Files Changed

1. **`src/jambandnerd/models/phish/experiments.py`**
   - Updated module docstring to reflect stacked model as incumbent
   - Added `PHISH_COMBO_SWEEP` with 7 HP variants
   - Registered in `PHISH_SWEEPS` dict

2. **`tests/models/test_phish_model.py`**
   - Updated `test_sweeps_are_registered()` to expect `combo_sweep`
   - Added `test_combo_sweep_uses_stacked_base_predictor()`

### Experiments

All 7 variants use `base_predictor_path="jambandnerd.models.phish.experiments.PhishFastPlusNotebookRankVenueRun"` with HP overrides:

| Slug | HP Overrides |
|---|---|
| combo_stack_leaves15 | num_leaves=15 |
| combo_stack_minleaf10 | min_data_in_leaf=10 |
| combo_stack_minleaf20 | min_data_in_leaf=20 |
| combo_stack_leaves15_minleaf10 | num_leaves=15, min_data_in_leaf=10 |
| combo_stack_leaves15_minleaf20 | num_leaves=15, min_data_in_leaf=20 |
| combo_stack_lr003_r700 | learning_rate=0.03, rounds=700 |
| combo_stack_leaves15_lr003_r700 | num_leaves=15, lr=0.03, rounds=700 |

## Commands Run

```bash
# Sweep execution
uv run python scripts/run_experiment.py --band phish --sweep combo_sweep --shows 100 --snapshot-root .snapshots/phish_phase_b

# Individual experiments (for faster iteration on remaining)
uv run python scripts/run_experiment.py --band phish --sweep combo_sweep --shows 100 --snapshot-root .snapshots/phish_phase_b --only combo_stack_leaves15_minleaf10
uv run python scripts/run_experiment.py --band phish --sweep combo_sweep --shows 100 --snapshot-root .snapshots/phish_phase_b --only combo_stack_lr003_r700
```

## Results

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | vs Incumbent |
|---|---|---|---|---|---|---|
| **Incumbent** | **0.4186** | **0.2929** | 0.2453 | 0.5442 | 0.2831 | — |
| combo_stack_leaves15_minleaf10 | 0.4163 | 0.2859 | 0.2408 | 0.5467 | 0.2779 | -0.0023 |
| combo_stack_lr003_r700 | 0.4158 | 0.2869 | 0.2448 | 0.5448 | 0.2823 | -0.0028 |
| combo_stack_minleaf10 | 0.4102 | 0.2788 | 0.2448 | 0.5412 | 0.2830 | -0.0084 |
| combo_stack_leaves15 | 0.4102 | 0.2737 | 0.2392 | 0.5412 | 0.2760 | -0.0084 |
| combo_stack_minleaf20 | 0.4099 | 0.2798 | 0.2408 | 0.5456 | 0.2827 | -0.0087 |
| combo_stack_leaves15_minleaf20 | 0.4087 | 0.2717 | 0.2408 | 0.5406 | 0.2778 | -0.0099 |
| combo_stack_leaves15_lr003_r700 | 0.4065 | 0.2717 | 0.2364 | 0.5412 | 0.2725 | -0.0121 |

**Best challenger**: `combo_stack_leaves15_minleaf10` (dual=0.4163) — still **-0.0023 below incumbent**

## Conclusion

**Phish Phase B cheap-combo pass is complete. No promotion.**

### Key Findings

1. **No HP variant clears promotion bar**: Best challenger (0.4163) is 0.0023 below incumbent (0.4186), far from the +0.005 threshold (0.4236).

2. **p@10 regression pattern**: All challengers show p@10 regression (0.2717–0.2869 vs incumbent 0.2929). The incumbent's stronger p@10 signal is not replicated by HP tuning alone.

3. **HP defaults near-optimal**: The stacked model's default HP (leaves=31, min_leaf=5, lr=0.05, rounds=200) appears well-tuned for this feature set. Smaller trees (leaves=15) and stronger regularization (min_leaf=10/20) consistently underperform.

4. **lr=0.03, rounds=700 not beneficial**: Unlike WSP (where lr=0.03, rounds=700 was part of the winning combo), Phish's slower learning rate variants regress.

### Files Changed

- `src/jambandnerd/models/phish/experiments.py` — Added `PHISH_COMBO_SWEEP` (7 configs), updated docstring
- `tests/models/test_phish_model.py` — Updated sweep assertions, added base predictor test

### Validation Status

- `pytest tests/models/test_phish_model.py tests/models/test_model_registry.py`: 26 passed
- `ruff check src/jambandnerd/models/phish/experiments.py tests/models/test_phish_model.py`: 0 issues
- No registry/metadata changes (no promotion candidate)

## Artifacts

- 7 sweep result summaries in `backtests/`:
  - `phish_phish_fast_gbm_v2_feat_notebook_rank_venue_run_combo_stack_*_summary.json`

## Next Steps

1. ✅ Phish cheap-combo pass documented as complete
2. **Shift Phish work to**:
   - Diagnostics (feature importance analysis, error case studies)
   - Larger architecture change (new feature families, different modeling approach)
3. Continue with other band optimizations or website integration work

## Band Status After This Session

| Band | Model | dual | Status |
|---|---|---|---|
| Goose | GooseFastRankPredictor | 0.409 | Promoted |
| Phish | PhishFastPlusNotebookRankVenueRun | 0.419 | **Incumbent held (no combo improvement)** |
| UM | UMFastPredictorV2 | 0.343 | Promoted |
| WSP | WSPFastPredictor V2 | 0.448 | Promoted |
| Billy | BillyFastPredictorV10 | 0.388 | Local optimum |
| Eggy | — | — | Excluded from Phase B |
