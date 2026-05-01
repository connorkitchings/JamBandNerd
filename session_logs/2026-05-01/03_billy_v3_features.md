# Billy V3 — WP-Inspired Rotation + Short-Window Features

## Goal

Extend BillyFastPredictorV2 (dual_score=0.374) with rotation analytics inspired by the
Widespread Panic setlist model methodology. Push dual_score above 0.374, targeting p@10≥0.35
or r@50≥0.50.

## Motivation

WP model review revealed the core idea missing from V2: knowing a song's *expected* gap
(based on how frequently it's played), not just its raw current gap. A song at gap=15 is
very different depending on whether it plays every 10 shows vs every 30.

## Features Added (V3 vs V2)

| Feature | Formula | Purpose |
|---------|---------|---------|
| `plays_past_3` | cumsum window 3 shows | Hot-song short window |
| `plays_past_5` | cumsum window 5 shows | Hot-song medium window |
| `overdue_ratio` | `gap_shows × career_play_pct` | Crude overdue signal |
| `avg_ltp_recent` | `min(25,j) / p25.clip(1)` | Expected gap from recent 25-show frequency |
| `ltp_diff_recent` | `gap_shows - avg_ltp_recent` | Explicit overdue vs recent expectation |

Also **fixed `same_venue_run_position` predict-time bug**: V2 always returned 0.0 at predict
time because venue context was never passed through. V3 correctly uses `target_show_context`.

## Implementation

- `src/jambandnerd/models/billy/fast_predictor.py`:
  - Added `BILLY_FAST_V3_FEATURE_COLS` constant (16 features = V2's 11 + 5 new)
  - Added `BillyFastPredictorV3` subclass overriding both hooks and `MODEL_VERSION`
  - Base class hooks updated to accept `gap_e`, `career_pct`, `target_show_context` params
  - V2 hooks updated to accept (but not use) new params for forward compatibility
  - `train()` and `predict()` updated to pass `gap_e`, `career_pct`, `target_show_context` to hooks
- `src/jambandnerd/models/registry.py`: V2 → V3 as default for "billy"
- `tests/models/test_billy_model.py`: Added 2 V3 tests, updated registry assertion to expect V3

## Backtest Results (100 shows, 2025-02-14 – 2026-04-18)

| Model | dual_score | p@10 | r@50 |
|---|---|---|---|
| GBM v2 (baseline) | 0.374 | 0.327 | 0.422 |
| **GBM v3 (promoted)** | **0.377** | 0.322 | **0.432** |

- dual_score: +0.003 (+0.8%) — marginal improvement, meets promotion threshold
- p@10: −0.005 (−1.5%) — slight regression, still short of 0.40 target
- r@50: +0.010 (+2.4%) — meaningful progress toward 0.50 target

## Decision

V3 promoted per pre-agreed criterion (dual_score > 0.374). V2 retained as parent class.

## Commands Run

```bash
uv run pytest tests/models/test_billy_model.py -q
uv run python scripts/run_phase_b_backtest.py \
  --band billy \
  --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictorV3 \
  --shows 100 \
  --snapshot-root .snapshots/billy_phase_b \
  --out-dir backtests/
uv run black src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py
uv run ruff check src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py
```

## Artifacts

- `backtests/billy_billy_fast_gbm_v3_summary.json`
- `backtests/billy_billy_fast_gbm_v3_100shows.jsonl`

## Next Steps

- p@10 target (0.40) still well out of reach — gap is large (0.322 vs 0.40)
- Candidates to try:
  1. Venue song affinity features (per-venue play rate)
  2. Set position encoding (opener tendency, encore, etc.)
  3. HP tuning: num_leaves 31→63, rounds 200→400, reg_alpha/lambda=0.1
  4. Goose model improvements (deferred)
