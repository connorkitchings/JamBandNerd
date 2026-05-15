# Billy Strings Phase B Diagnostics

## Goal

Implement a reusable Phase B feature-diagnostics workflow before adding more
BillyFast model features.

## Constraints

- Keep `BILLY_FAST_FEATURE_COLS`, `MODEL_VERSION`, registry, and metadata unchanged.
- Do not touch the unrelated dirty Goose files on `feat/three-stage-forecasting`.
- Analyze current BillyFast features plus offline candidate run/tour/same-venue
  context features.

## Commands Run

```bash
uv run pytest tests/models/test_billy_model.py -q
uv run pytest tests/scripts/test_diagnose_phase_b_features.py -q
uv run python scripts/diagnose_phase_b_features.py \
  --band billy \
  --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictor \
  --shows 25 \
  --snapshot-root .snapshots/billy_phase_b
uv run python scripts/diagnose_phase_b_features.py \
  --band billy \
  --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictor \
  --shows 100 \
  --snapshot-root .snapshots/billy_phase_b
uv run ruff check src/jambandnerd/models/billy/fast_predictor.py scripts/diagnose_phase_b_features.py tests/models/test_billy_model.py tests/scripts/test_diagnose_phase_b_features.py
uv run black --check src/jambandnerd/models/billy/fast_predictor.py scripts/diagnose_phase_b_features.py tests/models/test_billy_model.py tests/scripts/test_diagnose_phase_b_features.py
git diff --check -- scripts/README.md src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py scripts/diagnose_phase_b_features.py tests/scripts/test_diagnose_phase_b_features.py session_logs/2026-05-01/01_billy_phase_b_diagnostics.md
```

## Files And Artifacts

- `src/jambandnerd/models/billy/fast_predictor.py` — added
  `build_diagnostic_training_frame()` and diagnostic-only candidate feature columns.
- `scripts/diagnose_phase_b_features.py` — new reusable diagnostics script that
  writes Markdown and JSON reports.
- `tests/models/test_billy_model.py` — BillyFast diagnostic-frame coverage.
- `tests/scripts/test_diagnose_phase_b_features.py` — diagnostics helper smoke test.
- `scripts/README.md` — documents the diagnostics entrypoint.
- `.snapshots/billy_phase_b/diagnostics/billy_billy_fast_gbm_v1_25shows.{md,json}`
- `.snapshots/billy_phase_b/diagnostics/billy_billy_fast_gbm_v1_100shows.{md,json}`

## Validation

- `tests/models/test_billy_model.py`: 11 passed.
- `tests/scripts/test_diagnose_phase_b_features.py`: 1 passed.
- 25-show diagnostics wrote Markdown and JSON artifacts.
- 100-show diagnostics wrote Markdown and JSON artifacts.
- Ruff and Black checks passed for the touched Python files.
- Scoped `git diff --check` passed for the Billy diagnostics files.
- Full `git diff --check` remains blocked by pre-existing unrelated
  `tests/models/test_goose_model.py` whitespace.

## Findings

- 100-show diagnostic frame: 2,920,938 rows, positive rate 0.0552.
- Highest diagnostic gain features: `plays_past_50` (949.53), `gap_shows`
  (563.88), `tour_position` (443.52), `career_play_pct` (262.26),
  `month_play_rate` (228.35).
- Candidate context features have signal worth testing: `tour_position` has
  high diagnostic gain despite near-zero linear correlation; `diff_25_to_50`,
  `show_position_in_run`, and `same_venue_run_position` have smaller but
  non-zero gain.
- Same-venue prior-play features are very sparse (96.8% zero), so they should be
  treated as optional/ablation candidates rather than all-or-nothing additions.

## Next Step

Run a BillyFast candidate-feature ablation/backtest:

1. Add a new BillyFast candidate version that includes `tour_position` only.
2. Backtest 100 shows against `.snapshots/billy_phase_b`.
3. If it improves F1@25/p@25, test adding `diff_25_to_50`,
   `show_position_in_run`, and `same_venue_run_position`.
4. Keep sparse same-venue prior-play count/share features out until an ablation
   shows a clear lift.
