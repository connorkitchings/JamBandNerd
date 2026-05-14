# Session 03: Billy Strings HP Sweep and V10 Promotion

## Goal

Run a systematic hyperparameter sweep on BillyFastPredictorV3 to find an
improved configuration. Prior experiments (V4-V9) all failed; the sweep
isolates individual parameter changes to identify what actually helps.

## Constraints

- V3 features (16) and 75-show training window are fixed.
- Compare against V3 baseline (dual=0.377).
- Do not modify registry/metadata until a winner is confirmed.

## Experiments Run

### Prior rejected experiments (for context)

| Version | Change | dual | Delta |
|---------|--------|------|-------|
| V7 | Full-history training | 0.297 | -0.080 |
| V8 | 150-show window | 0.305 | -0.072 |
| V9 | +notebook_rank_score | 0.303 | -0.074 |

### HP Sweep (13 single-variable experiments)

| Experiment | dual | Delta |
|-----------|------|-------|
| **hp_leaves15** | **0.3874** | **+0.0104** |
| hp_lr003 | 0.3852 | +0.0082 |
| hp_lambda01 | 0.3843 | +0.0073 |
| hp_minleaf10 | 0.3837 | +0.0067 |
| hp_minleaf3 | 0.3830 | +0.0060 |
| hp_rounds100 | 0.3820 | +0.0050 |
| hp_minleaf20 | 0.3810 | +0.0040 |
| hp_rounds300 | 0.3706 | -0.0064 |
| hp_leaves63 | 0.3699 | -0.0071 |
| hp_lr007 | 0.3684 | -0.0086 |
| hp_rounds500 | 0.3578 | -0.0192 |
| hp_lr010 | 0.3495 | -0.0275 |
| hp_leaves127 | 0.3407 | -0.0363 |

### Combo Sweep (6 experiments combining top parameters)

| Experiment | dual | Delta |
|-----------|------|-------|
| **combo_leaves15_minleaf10** | **0.3879** | **+0.0109** |
| combo_leaves15_lr003_lambda01 | 0.3876 | +0.0106 |
| combo_leaves15_lr003_minleaf10 | 0.3862 | +0.0092 |
| combo_leaves15_lambda01 | 0.3858 | +0.0088 |
| combo_leaves15_lr003_lambda01_minleaf10 | 0.3854 | +0.0084 |
| combo_leaves15_lr003 | 0.3815 | +0.0045 |

## Result

**Winner: combo_leaves15_minleaf10 → BillyFastPredictorV10**
- dual=0.3879 (+0.0109 vs V3)
- num_leaves=15 (31→15), min_data_in_leaf=10 (5→10)
- All other params at V3 defaults

## Key Findings

1. **Less capacity helps Billy.** Every experiment with fewer leaves or more
   regularization beat V3. Every experiment with more capacity (leaves=63,
   127) or more rounds (300, 500) regressed. Billy's 75-show training signal
   is too thin for complex models.

2. **Full-history training is actively harmful for Billy.** Unlike Goose
   (+0.025 from full history), Billy's rotation patterns change rapidly.
   The 75-show window is a beneficial freshness filter.

3. **notebook_rank_score doesn't help Billy.** Unlike Goose (+0.006) and
   Phish (+0.014), the feature is redundant with existing features given
   Billy's limited training signal.

4. **Billy is structurally different from Goose/Phish.** High touring
   frequency (~200+ shows/year), rapidly evolving catalog, and cover song
   dynamics make Billy a fundamentally different modeling problem.

## Files Changed

- `src/jambandnerd/models/billy/fast_predictor.py`: Added `_start_col()`
  hook, V7/V8/V9/V10 classes, updated `BillyFastBaselinePredictor` alias to V10
- `src/jambandnerd/models/billy/experiments.py`: New — HP sweep + combo sweep configs
- `src/jambandnerd/models/metadata.py`: Updated Billy model_version to v10
- `scripts/run_experiment.py`: Added Billy to `_BASE_PREDICTOR_PATHS`
- `tests/models/test_billy_model.py`: Updated version assertion

## Commands Run

```bash
uv run python scripts/run_experiment.py --band billy --sweep hp_sweep --shows 100 --snapshot-root .snapshots/billy_phase_b
uv run python scripts/run_experiment.py --band billy --sweep combo_sweep --only <slug> --shows 100 --snapshot-root .snapshots/billy_phase_b
uv run pytest tests/models/test_billy_model.py -q
```

## Validation

- 25/25 Billy model tests pass
- V10 registered as `BillyFastBaselinePredictor` in registry
- Model version: `billy_fast_gbm_v10_hp_tuned`

## Next Step

V10 dual=0.388 is still well below the 0.40 target. To close the gap, a
fundamentally different architecture may be needed (two-stage ranking,
blending, or different learning objective).
