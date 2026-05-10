# Goose V2 Optimization Sweep — Session Summary

## Goal

Apply lessons from WSP/Billy/UM/Phish optimization sweeps to Goose. Test WSP-proven long-rotation features (`plays_past_100`, `diff_50_to_100`, `long_rotation_pressure`) and cross-band HP combos on the current 17-feature production baseline (dual=0.409).

## Constraints

- No Supabase writes; local `.snapshots/goose_phase_b` evaluation window
- Feature branch: `feat/wsp-combo-sweep`
- Incumbent: `GooseFastRankPredictor` (= `GooseFastPlusNotebookRank`, 17 features, dual=0.409)
- No promotion without clear dual improvement over incumbent

## Changes

### Source code
- `src/jambandnerd/models/goose/experiments.py` — Added `GooseFastPlusRotation` class (20 features: 17 base + 3 rotation), added `GOOSE_V2_SWEEP` (11 configs testing HP × feature combos on 17/20-feature baselines), registered in `GOOSE_SWEEPS`

### Tests
- `tests/models/test_goose_model.py` — Added `TestGooseExperimentClasses` with 6 tests: `GooseFastPlusPlaysPastYear` defaults, `GooseFastPlusNotebookRank` defaults + train/predict, `GooseFastPlusRotation` defaults + train/predict, `GOOSE_V2_SWEEP` registration

## Commands Run

```bash
# Lint and tests
uv run ruff check src/jambandnerd/models/goose/experiments.py tests/models/test_goose_model.py
uv run python -m pytest tests/models/test_goose_model.py tests/models/test_goose_features.py -v  # 50 passed

# Experiment sweeps
uv run python scripts/run_experiment.py --band goose --sweep v2_sweep --only feat_rotation --shows 100
uv run python scripts/run_experiment.py --band goose --sweep v2_sweep --shows 50
uv run python -c "..."  # run incumbent baseline on 50-show window

# Individual experiments
uv run python scripts/run_experiment.py --band goose --sweep v2_sweep --only hp_lr003_r400 --shows 100
uv run python scripts/run_experiment.py --band goose --sweep v2_sweep --only combo_rotation_leaves15_minleaf10 --shows 50
uv run python scripts/run_experiment.py --band goose --sweep v2_sweep --only combo_rotation_leaves15_lr007_lambda01 --shows 50
uv run python scripts/run_experiment.py --band goose --sweep v2_sweep --only hp_leaves15_minleaf10 --shows 50
```

## Results

### 100-show window

| Experiment | dual | vs Incumbent (0.409) |
|---|---|---|
| feat_rotation (20 feats, default HPs) | 0.408 | −0.001 |
| hp_lr003_r400 (17 feats, WSP-style HP) | 0.399 | −0.010 |

### 50-show window (incumbent baseline: 0.4019)

| Experiment | dual | Δ |
|---|---|---|
| hp_lr003_r400 (17 feat) | 0.391 | −0.011 |
| hp_leaves15_minleaf10 (17 feat) | 0.396 | −0.006 |
| feat_rotation (20 feat) | 0.397 | −0.005 |
| combo_rotation_leaves15_minleaf10 (20 feat) | 0.396 | −0.006 |
| combo_rotation_leaves15_lr007_lambda01 (20 feat) | 0.402 | +0.000 |

### Key findings

1. **Long-rotation features do not help Goose.** Despite being worth +0.014 dual for WSP, `plays_past_100`, `diff_50_to_100`, and `long_rotation_pressure` are net-neutral or slightly negative for Goose. Goose's ~450-show history is too short for a 100-show rotation window to carry signal.

2. **Cross-band HP tuning does not help.** Every HP change from WSP (lr=0.03), Billy (leaves=15, min_leaf=10), and UM (leaves=15, lr=0.07, lambda=0.1) regresses vs the default params (leaves=31, lr=0.05, rounds=200, min_data=5).

3. **Goose is at ceiling with the current LightGBM rank_xendcg architecture.** All tested configurations — 11 experiments across HP changes and feature additions — fail to beat the incumbent. The UM-style HP + rotation combo (0.402 on 50-show) is the closest challenger but statistically ties.

4. **Goose has different dynamics than other bands.** WSP, Billy, and UM all showed some response to HP tuning (WSP: +0.014 from rotation features; UM: +0.020 from HP tuning; Billy: +0.011 from HP tuning). Goose resists every change. The shorter history and smaller catalog may require a fundamentally different approach.

## Validation Status

- **Lint**: `ruff check` — all passed
- **Tests**: 50/50 passed (goose model + goose features)
- **Full test suite**: Not run
- **Quality gates**: Not run

## Conclusion

**Goose joins WSP, Billy, and UM at ceiling.** The current LightGBM `rank_xendcg` architecture with matrix-based features can't push beyond the 0.409 dual incumbent. Future improvements require:
- A different model architecture (logistic regression, CatBoost, XGBoost)
- Set-level prediction or sequence models
- Larger catalog / more history (passage of time)

Phish remains the only band below ceiling with documented cleanup opportunities (dead venue-run features, `month_play_rate` removal, show-type flags).

## Next Step

Phish V2 cleanup — remove dead features identified in 2026-05-07 diagnostics, test show-type flags, and re-run the combo sweep on the cleaned baseline.
