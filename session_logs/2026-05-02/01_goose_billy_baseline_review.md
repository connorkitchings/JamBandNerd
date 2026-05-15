# Goose & Billy Baseline Review + Goose Feature Distillation Kickoff

## Goal

Refresh legacy baseline comparisons (Notebook, Deal) against the current Goose
and Billy active models, confirm which bands have a standard-bearer, and start
Goose feature distillation to find a minimal feature set that beats Notebook.

## Constraints

- All backtests on the same 100-show local snapshot windows already used for
  Phase B experiments (`.snapshots/goose_phase_b`, `.snapshots/billy_phase_b`).
- Goose distillation must use logistic (DealPredictor-based) architecture,
  test co-occurrence last, and target `dual_score ≥ 0.408`.
- Billy is already accepted as V3; no promotion change needed.

## Key Findings

### Billy: Clear Standard-Bearer

BillyFastPredictorV3 (`billy_fast_gbm_v3`) decisively beats all baselines on
the 100-show window:

| Model | dual | p@10 | r@50 |
|-------|------|------|------|
| **BillyFast V3** | **0.377** | **0.322** | **0.432** |
| Notebook | 0.333 | 0.294 | 0.373 |
| Deal | *stalled* | — | — |

V3 beats Notebook by +9.5% p@10, +15.8% r@50, +13.2% dual. No further action
needed — V3 is the standard-bearer.

### Goose: Notebook Beats the Incumbent

GoosePredictor v1 (`goose_phase_b_v1`, Deal-based logistic + Goose features)
does NOT clearly beat the simple rule-based Notebook baseline:

| Model | dual | p@10 | r@50 | F1@25 |
|-------|------|------|------|-------|
| **Notebook** | **0.408** | **0.284** | 0.531 | **0.279** |
| GoosePredictor v1 | 0.399 | 0.265 | **0.534** | 0.270 |
| gbm_notebook_blend v4 | 0.383 | 0.239 | 0.526 | 0.258 |

The 100-show GBM+Notebook blend sweep confirmed that **every alpha > 0.0
degrades from pure Notebook**. The GBM signal is actively harmful for Goose
ranking. Even GoosePredictor v1 (logistic, not GBM) loses to Notebook on dual
(0.399 vs 0.408) and precision (0.265 vs 0.284), only winning recall by 0.003.

## Commands Run

```bash
# Fresh Notebook baselines (100-show)
uv run python scripts/run_phase_b_backtest.py --band goose \
  --predictor jambandnerd.models.notebook.model.NotebookPredictor \
  --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/

uv run python scripts/run_phase_b_backtest.py --band billy \
  --predictor jambandnerd.models.notebook.model.NotebookPredictor \
  --shows 100 --snapshot-root .snapshots/billy_phase_b --out-dir backtests/

# Fresh Deal baselines (100-show, started but not completed)
uv run python scripts/run_phase_b_backtest.py --band goose \
  --predictor jambandnerd.models.deal.model.DealPredictor \
  --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/ &

uv run python scripts/run_phase_b_backtest.py --band billy \
  --predictor jambandnerd.models.deal.model.DealPredictor \
  --shows 100 --snapshot-root .snapshots/billy_phase_b --out-dir backtests/ &

# Goose distilled notebook-only (50-show screening, started but not completed)
uv run python scripts/run_phase_b_backtest.py --band goose \
  --predictor jambandnerd.models.goose.distilled.GooseDistilledNotebookPredictor \
  --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/ &

# Validation
uv run pytest tests/models/test_goose_model.py tests/models/test_model_registry.py -q
uv run ruff check src/jambandnerd/models/goose/ src/jambandnerd/models/notebook/model.py scripts/run_phase_b_backtest.py
```

## Files Changed

- `src/jambandnerd/models/notebook/model.py` — added `**kwargs` to `__init__`,
  added `MODEL_VERSION = "notebook_v1"`. Fixes backtest script compatibility.
- `scripts/run_phase_b_backtest.py` — unwraps `predict()` return when it's a
  tuple (NotebookPredictor returns `(list, dict)`).
- `src/jambandnerd/models/goose/distilled.py` — **new file**. Feature-family
  distillation predictor with 8 named families and 7 convenience subclasses
  for backtest screening.
- `src/jambandnerd/models/goose/__init__.py` — exports new distilled classes.
- `tests/models/test_goose_model.py` — 8 new tests for distilled predictor
  (defaults, band rejection, unknown family, empty families, dedup, version,
  train/predict, feature ordering).
- `backtests/goose_notebook_v1_summary.json` — fresh 100-show Notebook baseline.
- `backtests/billy_notebook_v1_summary.json` — fresh 100-show Notebook baseline.
- Backtest artifacts renamed from `*_unknown_*` to `*_notebook_v1_*`.

## Validation Status

- `pytest tests/models/test_goose_model.py tests/models/test_model_registry.py`: 
  **33 passed** (26 goose + 7 registry)
- `ruff check` on changed files: clean after auto-fix of import ordering.
- Full `npm run verify:python` was NOT run (backtests were in flight).
- Deal baselines for both bands were NOT completed (Goose at ~30/100, Billy stalled).
- Goose distilled notebook-only backtest NOT completed (~7/50 when session ended).

## Next Step

Resume the Goose feature-distillation backtest sequence:

```bash
# 1. Complete notebook-only baseline (50-show, already started)
uv run python scripts/run_phase_b_backtest.py --band goose \
  --predictor jambandnerd.models.goose.distilled.GooseDistilledNotebookPredictor \
  --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/

# 2. +gap
uv run python scripts/run_phase_b_backtest.py --band goose \
  --predictor jambandnerd.models.goose.distilled.GooseDistilledNotebookGapPredictor \
  --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/

# 3. +recency → GooseDistilledNotebookGapRecencyPredictor
# 4. +debut → GooseDistilledNotebookGapRecencyDebutPredictor
# 5. +set_position (no venue) → GooseDistilledNoVenuePredictor
# 6. +venue → GooseDistilledFullBasePredictor
# 7. +cooccurrence → GooseDistilledFullBaseCoocPredictor
```

Stop adding families when a family causes `dual_score` regression below the
current best. After identifying the winning feature set at 50-show, validate
at 100-show. If no family combination reaches `dual ≥ 0.408`, move to Path B
(feature diagnostics / GBM permutation importance) or Path D (Reciprocal Rank
Fusion).

Also: complete the Goose and Billy Deal baselines (100-show) for a full
comparison table. Billy Deal is ~10 min/show — run overnight.
