# Session: Enrich Prediction Output for All Bands

**Date**: 2026-05-18
**Branch**: `feat/enrich-prediction-output`
**Commit**: `474dde7`

## Goal

Enrich prediction output for UM, Phish, WSP, and Billy Strings with `current_gap`, `recent_plays_50`, `LTP`, and `plays_past_year` fields (matching Goose), and fix Goose's inflated probabilities (100%/98%/96% caused by rank-based overwrite in `_merge_rank_guard_predictions`).

## Constraints

- All bands share `serialize_deal_predictions` as the serializer (registry.py:265)
- `PhishFastPredictor.predict()` is inherited by UM (`UMFastPredictorV2`) and WSP (`WSPFastPredictor`) — fixing it fixes 3 bands
- `BillyFastPredictor.predict()` fixes Billy independently
- User strongly prefers LightGBM model probabilities flow through untouched
- Pre-existing test failure: `tests/test_version_sync.py` (pyproject `0.3.0` vs web `1.0.1`) — unrelated
- Web app changes deferred to a separate session

## Commands Run

```bash
# Tests
uv run pytest --tb=short -q --ignore=tests/pipeline/test_live_band_smoke.py --ignore=tests/test_version_sync.py

# Backtests (50 shows each)
uv run python scripts/run_backtest.py --band goose --shows 50 --no-incremental
uv run python scripts/run_backtest.py --band phish --shows 50 --no-incremental
uv run python scripts/run_backtest.py --band um --shows 50 --no-incremental
uv run python scripts/run_backtest.py --band wsp --shows 50 --no-incremental
uv run python scripts/run_backtest.py --band billy --shows 50 --no-incremental

# Live predictions
uv run python scripts/generate_live_predictions.py --band goose --require-output
uv run python scripts/generate_live_predictions.py --band phish --require-output
uv run python scripts/generate_live_predictions.py --band um --require-output
uv run python scripts/generate_live_predictions.py --band wsp --require-output
uv run python scripts/generate_live_predictions.py --band billy --require-output
```

## Files Changed

- `src/jambandnerd/models/phish/fast_predictor.py` — `PhishFastPredictor.predict()` returns `DealPrediction` with enrichment fields; `last_play_dates` added to cache; `PhishPrediction` dataclass removed
- `src/jambandnerd/models/billy/fast_predictor.py` — Same pattern: `DealPrediction` return, `last_play_dates` cache, `BillyPrediction` removed
- `src/jambandnerd/models/goose/model.py` — `_merge_rank_guard_predictions()` fixed to preserve LightGBM probabilities
- `src/jambandnerd/models/goose/experiments.py` — Identical fix to second copy of `_merge_rank_guard_predictions()`
- `tests/models/test_phish_model.py` — Updated import from `PhishPrediction` to `DealPrediction`
- `docs/contributor/model_readiness.md` — Updated readiness notes
- `.agent/PLAYBOOK.md` — Added 3 lessons from this session

## Validation

- 628 tests pass
- Skipped: `test_live_band_smoke` (requires Supabase), `test_version_sync` (pre-existing unrelated failure)
- Quality gates (`npm run verify:*`) not run — web changes deferred

## Backtest Results (50 shows)

| Band  | p@10  | r@50  | dual  |
|-------|-------|-------|-------|
| WSP   | 0.354 | 0.583 | 0.468 |
| Goose | 0.246 | 0.591 | 0.418 |
| Phish | 0.276 | 0.540 | 0.408 |
| Billy | 0.310 | 0.411 | 0.360 |
| UM    | 0.152 | 0.398 | 0.275 |

## Live Predictions Generated

- Goose: 2026-05-22
- Phish: 2026-07-07
- UM: 2026-05-22
- WSP: 2026-06-13
- Billy: 2026-07-14

## Next Step

Sigmoid-on-ranking-scores may still produce somewhat inflated probabilities for all bands (rank_xendcg scores aren't calibrated logits). Platt scaling or isotonic regression calibration could address this as a follow-up.
