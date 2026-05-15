# Goose v2 — Phase 2 Framework

## Goal

Build everything needed to run two Goose v2 backtest variants (logistic + GBM)
and apply the Phase B promotion gate — short of running the actual 3.5h backtests.

## Decisions Locked

- **Feature scope = Tier A + Tier B.** `transformations/gaps.py` now plumbs
  `set_number`, `song_position`, `encore` through `historical_plays` for ALL
  bands (additive, other bands unaffected).
- **Connor runs backtests locally** (~3.5h per variant). Scripts are ready.
- **Tiebreaker** if both variants pass the +2pp gate: higher `dual_score`
  (α = 0.5). Tie at 4 decimals → prefer logistic.

## Files Created

| File | Purpose |
|---|---|
| `src/jambandnerd/models/goose/features.py` | Tier A + Tier B Goose feature module |
| `scripts/run_phase_b_backtest.py` | Single-variant backtest → `BacktestSummary` JSON |
| `scripts/promote_phase_b_winner.py` | Load two summaries, apply gate, print decision |
| `tests/pipeline/test_historical_plays_set_columns.py` | Verify set column plumbing |
| `tests/models/test_goose_features.py` | Leakage + computation tests for Goose features |

## Files Modified

| File | Change |
|---|---|
| `src/jambandnerd/transformations/gaps.py` | Extend `_compute_base_features` to optionally carry `set_number`, `song_position`, `encore` from `setlists_df` |
| `src/jambandnerd/models/deal/model.py` | Add `_build_training_frame` and `_get_candidate_features` hooks to enable clean subclassing |
| `src/jambandnerd/models/gbm/predictor.py` | Same hooks for `BandGbmPredictor` |
| `src/jambandnerd/models/goose/model.py` | Add `GooseLogisticV2Predictor` and `GooseGbmV2Predictor`; preserve `GoosePredictor` (v1) unchanged |

## Key Contracts

**`compute_goose_song_features(historical_plays, *, target_show_date)`**
in `models/goose/features.py`: Returns a DataFrame keyed by `song_name` with
8 new feature columns (Tier A: `dow_play_rate`, `month_play_rate`,
`show_position_in_run`, `tour_position`; Tier B: `set1_play_rate`,
`set2_play_rate`, `encore_rate`, `mean_song_position`). Tier B defaults to 0.0
when set columns are absent in `historical_plays`.

**`augment_training_frame(training_frame, historical_plays)`**: Loops over
unique `target_show_date` values in the training frame, replicates the correct
history truncation (same `prediction_date = target_show_date - 1 day` used by
`build_training_frame`), and merges Goose features in. Leakage-safe.

**`GooseLogisticV2Predictor`** (`MODEL_VERSION = "goose_phase_b_v2_logistic"`):
Overrides `_build_training_frame` (augments) and `_get_candidate_features`
(merges Goose features on `song_name`). Uses `GOOSE_V2_FEATURE_COLUMNS`
(= 15 base + 8 Goose-specific = 23 features).

**`GooseGbmV2Predictor`** (`MODEL_VERSION = "goose_phase_b_v2_gbm"`): Same
feature scope via the same hook pattern. Subclasses `BandGbmPredictor`.

## Backtest Commands (Connor runs)

```bash
# Baseline
uv run python scripts/run_phase_b_backtest.py \
    --band goose \
    --predictor jambandnerd.models.goose.model.GoosePredictor \
    --shows 100 --out-dir backtests/

# Candidate A — logistic v2
uv run python scripts/run_phase_b_backtest.py \
    --band goose \
    --predictor jambandnerd.models.goose.model.GooseLogisticV2Predictor \
    --shows 100 --out-dir backtests/

# Candidate B — GBM v2
uv run python scripts/run_phase_b_backtest.py \
    --band goose \
    --predictor jambandnerd.models.goose.model.GooseGbmV2Predictor \
    --shows 100 --out-dir backtests/
```

Then apply the gate:
```bash
uv run python scripts/promote_phase_b_winner.py \
    --incumbent backtests/goose_goose_phase_b_v1_summary.json \
    --candidate backtests/goose_goose_phase_b_v2_logistic_summary.json

uv run python scripts/promote_phase_b_winner.py \
    --incumbent backtests/goose_goose_phase_b_v1_summary.json \
    --candidate backtests/goose_goose_phase_b_v2_gbm_summary.json
```

## Validation

```
npm run verify:python → 403 passed, 6 skipped
```

## Next Step

Connor runs the three backtests. Once summary JSONs are available, resume
session to apply `is_band_promotion_eligible` gate, decide the winner, and
update `src/jambandnerd/models/metadata.py` + (if GBM wins) `registry.py`.

Post-promotion: `npm run verify:python` + end-to-end smoke with
`generate_live_predictions.py --band goose`.
