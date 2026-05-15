# GooseMatrix V2 Experiment

## Goal

Apply the Billy speed/quality lessons to Goose by keeping the standalone matrix
ranker architecture, then adding only the highest-value Goose/Deal signals that
were missing from the first Goose matrix attempts.

## Implementation

Added `GooseMatrixPredictorV2` in
`src/jambandnerd/models/goose/fast_predictor.py`.

V2 keeps the V1 matrix LightGBM ranker and adds:

- Incumbent-parity recency features: `plays_past_year`, `plays_past_2yr`,
  `pct_shows_6mo`, `diff_6mo_to_1yr`.
- Incumbent-parity history features: `n_shows_same_venue`,
  `n_shows_same_state`, `debut_age_shows`, `novelty_rank`.
- Matrix-native selective co-occurrence features against recent anchors:
  `recent_anchor_cooc_mean`, `recent_anchor_cooc_max`,
  `last_show_cooc_mean`, `last_show_cooc_max`.

The model is exported for direct experiments, but the registry still points at
the incumbent Goose predictor.

## Validation

Commands:

```bash
uv run pytest tests/models/test_goose_model.py -q
uv run ruff check src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run black src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.fast_predictor.GooseMatrixPredictorV2 --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/
```

Results:

- Tests: 18 passed.
- Ruff: all checks passed.
- Black: 5 files unchanged.

## Backtest Result

`goose_matrix_gbm_v2`, 100-show `.snapshots/goose_phase_b` backtest:

- `p@10=0.245`
- `r@50=0.500`
- `F1@25=0.250`
- `dual=0.373`
- `dual_f1=0.209`

Comparators from the same 100-show snapshot:

- Incumbent `goose_phase_b_v1`: `dual=0.399`, `p@10=0.265`,
  `r@50=0.534`, `F1@25=0.270`.
- `goose_fast_gbm_v1`: `dual=0.378`, `p@10=0.246`, `r@50=0.511`,
  `F1@25=0.255`.
- `goose_matrix_gbm_v1`: `dual=0.377`, `p@10=0.244`, `r@50=0.510`,
  `F1@25=0.258`.

Artifacts:

- `backtests/goose_goose_matrix_gbm_v2_summary.json`
- `backtests/goose_goose_matrix_gbm_v2_100shows.jsonl`

## Decision

Do not promote V2.

The extra features did not recover quality and made the standalone matrix path
materially slower. The result weakens the case for further hand-added matrix
features as the next Goose path. The next Goose attempt should either:

- Use diagnostics/ablations to identify the specific incumbent signals the
  matrix ranker cannot reproduce.
- Revisit the incumbent logistic/Deal-derived path with targeted efficiency
  fixes.
- Test rank blending with a cheap matrix model only if it improves p@10 without
  eroding the incumbent's recall.
