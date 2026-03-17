# Cross-Band Verification

## Goal

- Verify that recent repo changes did not break data ingestion, transformation, or setlist prediction across all active bands.

## Scope

- Bands: `billy`, `eggy`, `goose`, `phish`, `um`, `wsp`
- Local confidence checks: model tests and collector tests
- Live checks: collection, prediction generation, freshness, prediction-table validation
- Targeted backtests: Goose and WSP for both models

## High-Level Results

| Band | Ingestion | Transformation + Prediction | Freshness | Backtest | Status |
|------|-----------|-----------------------------|-----------|----------|--------|
| billy | Collection completed, but song scrape timed out | Notebook + CK+ wrote fresh rows | No recent shows found | Not run | Review |
| eggy | Passed | Notebook + CK+ wrote fresh rows | 1 recent show missing setlist | Not run | Review |
| goose | Passed | Notebook + CK+ wrote fresh rows | No recent shows found | Notebook + CK+ passed (`--shows 10`) | Pass |
| phish | Passed | Notebook + CK+ wrote fresh rows | No recent shows found | Not run | Pass |
| um | Collection exited 0, but no new setlists scraped | Notebook + CK+ wrote fresh rows | 1 recent show missing setlist | Not run | Review |
| wsp | Failed on `wsp_shows_raw_source_url_key` duplicate constraint | Notebook + CK+ still wrote fresh rows from existing raw data | No recent shows found | Notebook + CK+ passed (`--shows 10`) | Fail |

## Important Notes

- `scripts/validate_prediction_tables.py` is not a reliable post-write validator for bands that already have farther-future `reference_date` rows. That affected Goose and UM. Their fresh writes were confirmed by querying the latest rows by `predicted_at` instead.
- Goose and WSP both had stale prediction rows before this verification. The smoke run refreshed both tables successfully for their current upcoming shows.
- WSP is the clearest actionable issue: ingestion currently fails on a duplicate `source_url` unique-constraint conflict even though downstream prediction still works on existing raw data.

## Commands Run

```bash
uv run python scripts/get_all_bands.py
uv run pytest tests/models/test_notebook_model.py tests/models/test_ckplus_model.py -q
uv run pytest tests/data_collection/test_goose_collector.py tests/data_collection/test_phish_collector.py tests/data_collection/test_billy_collector.py tests/data_collection/test_um_collector.py tests/data_collection/test_wsp_collector.py -q
uv run python scripts/validate_prediction_tables.py --max-age-hours 168

BAND=billy uv run python scripts/verify_data_freshness.py
BAND=eggy uv run python scripts/verify_data_freshness.py
BAND=goose uv run python scripts/verify_data_freshness.py
BAND=phish uv run python scripts/verify_data_freshness.py
BAND=um uv run python scripts/verify_data_freshness.py
BAND=wsp uv run python scripts/verify_data_freshness.py

PYTHONUNBUFFERED=1 uv run python scripts/run_billy_collection.py
PYTHONUNBUFFERED=1 uv run python scripts/run_eggy_collection.py
PYTHONUNBUFFERED=1 uv run python scripts/run_goose_collection.py
PYTHONUNBUFFERED=1 uv run python scripts/run_phish_collection.py
PYTHONUNBUFFERED=1 uv run python scripts/run_um_collection.py
PYTHONUNBUFFERED=1 uv run python scripts/run_wsp_collection.py

PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band billy --model notebook
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band billy --model ckplus
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band eggy --model notebook
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band eggy --model ckplus
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band goose --model notebook
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band goose --model ckplus
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band phish --model notebook
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band phish --model ckplus
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band um --model notebook
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band um --model ckplus
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band wsp --model notebook
PYTHONUNBUFFERED=1 uv run python scripts/generate_predictions.py --band wsp --model ckplus

uv run python scripts/validate_prediction_tables.py --band billy --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band eggy --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band goose --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band phish --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band um --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band wsp --max-age-hours 2

uv run python scripts/run_backtest.py --band goose --model notebook --shows 10
uv run python scripts/save_aggregate_accuracy.py --band goose --model notebook --shows 10
uv run python scripts/run_backtest.py --band goose --model ckplus --shows 10
uv run python scripts/save_aggregate_accuracy.py --band goose --model ckplus --shows 10
uv run python scripts/run_backtest.py --band wsp --model notebook --shows 10
uv run python scripts/save_aggregate_accuracy.py --band wsp --model notebook --shows 10
uv run python scripts/run_backtest.py --band wsp --model ckplus --shows 10
uv run python scripts/save_aggregate_accuracy.py --band wsp --model ckplus --shows 10
```

## Next Step

- Fix WSP collection’s duplicate `source_url` handling first, then tighten the post-write validator so it can validate the latest row by `predicted_at` instead of being masked by older farther-future `reference_date` rows.
