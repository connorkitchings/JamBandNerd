# Goose ThreeStagePredictor Wiring + Backtest Attempt

## Goal

- Fix the feature gap in `ThreeStagePredictor` (was wrapping vanilla `BandGbmPredictor`
  instead of the full Goose V2 feature set).
- Add `GooseThreeStagePredictor` to `goose/model.py` as the Goose-specific three-stage
  entry point.
- Run 100-show walk-forward backtests for three predictors to decide which to keep and
  which to retire.

## Constraints

- Do not add complexity — the goal is to reduce from 6 Goose predictor variants to ≤3
  by validating ThreeStage against the Notebook blend and retiring the loser.
- All changes must be backwards-compatible with existing `ThreeStagePredictor` callers.

## Commands Run

```bash
uv run pytest tests/models/ -q
uv run python scripts/run_phase_b_backtest.py --band goose \
    --predictor jambandnerd.models.goose.model.GoosePredictor \
    --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/
uv run python scripts/run_phase_b_backtest.py --band goose \
    --predictor jambandnerd.models.goose.model.GooseGbmNotebookBlendPredictor \
    --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/
uv run python scripts/run_phase_b_backtest.py --band goose \
    --predictor jambandnerd.models.goose.model.GooseThreeStagePredictor \
    --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/
```

## Files Changed

- `src/jambandnerd/models/three_stage/predictor.py` — Added `gbm_class: Type[BandGbmPredictor]`
  parameter to `ThreeStagePredictor.__init__` (backwards-compatible; defaults to
  `BandGbmPredictor`). Fixes the feature gap so Goose-specific subclasses can inject
  `GooseGbmV2Predictor` as Stage 1.
- `src/jambandnerd/models/goose/model.py` — Added `GooseThreeStagePredictor` (thin
  subclass of `ThreeStagePredictor`; defaults `gbm_class=GooseGbmV2Predictor`). Also
  added import of `ThreeStagePredictor`.
- `src/jambandnerd/models/goose/__init__.py` — Exported `GooseThreeStagePredictor`.

## Validation Status

- `uv run pytest tests/models/ -q`: **116 passed** (no regressions).
- Backtests: **incomplete** — all three processes were killed at shows 62/100, 56/100,
  and 52/100 after ~70 min wall time (ran in parallel, suffered CPU contention; each
  consumed ~60 min CPU at ~50% effective throughput). No output files were written
  (script writes atomically at the end).

## Backtest Runtime Note

Running three 100-show walk-forward backtests in parallel caused severe CPU contention
on a single machine (~50% effective CPU per process), tripling wall time. Estimated
~20 min per run when sequential.

## Next Step

Re-run backtests **sequentially** to get clean results:
```bash
for pred in \
  jambandnerd.models.goose.model.GoosePredictor \
  jambandnerd.models.goose.model.GooseGbmNotebookBlendPredictor \
  jambandnerd.models.goose.model.GooseThreeStagePredictor; do
  uv run python scripts/run_phase_b_backtest.py \
      --band goose --predictor $pred --shows 100 \
      --snapshot-root .snapshots/goose_phase_b --out-dir backtests/
done
```
Compare `dual_score` and `dual_f1_score`. If ThreeStage ≥ blend, retire
`GooseGbmV2Predictor`, `GooseGbmTop10V3Predictor`, and `GooseGbmNotebookBlendPredictor`.
