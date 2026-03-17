# Review Band Recheck

## Goal

- Recheck the remaining review bands (`um`, `eggy`, `billy`) after the WSP ingestion fix and prediction-validator fix, then close any issues that were actually verifier noise.

## Constraints

- Keep monitoring strict for completed shows.
- Do not suppress legitimate missing-setlist warnings for finished shows.

## Commands Run

```bash
BAND=um uv run python scripts/verify_data_freshness.py
uv run python scripts/diagnose_band_data.py --band um
PYTHONUNBUFFERED=1 uv run python scripts/run_um_collection.py

BAND=eggy uv run python scripts/verify_data_freshness.py
uv run python scripts/diagnose_band_data.py --band eggy
PYTHONUNBUFFERED=1 uv run python scripts/run_eggy_collection.py

BAND=billy uv run python scripts/verify_data_freshness.py
uv run python scripts/diagnose_band_data.py --band billy

uv run pytest tests/test_data_diagnostics_scripts.py -q
uv run python -m py_compile scripts/verify_data_freshness.py scripts/diagnose_band_data.py
```

## Files And Artifacts

- `scripts/verify_data_freshness.py`: now checks only completed shows by excluding today from the freshness window.
- `scripts/diagnose_band_data.py`: now diagnoses only completed recent shows and fetches setlist IDs by targeted recent-show lookup instead of scanning the full setlist table.
- `tests/test_data_diagnostics_scripts.py`: regression coverage for completed-show windowing and targeted setlist-ID lookup.

## Validation

- `um` now reports `✅ All recent shows have setlist data` and `diagnose_band_data.py` reports no issues.
- `eggy` now reports `✅ All recent shows have setlist data` and `diagnose_band_data.py` reports no issues.
- `billy` now reports `ℹ️ No recent completed shows found` and `diagnose_band_data.py` reports no issues for completed shows.
- Root cause: the previous review findings for `um` and `eggy` were same-day show false positives; the previous diagnostic noise for all three bands was caused by future scheduled shows and unbounded setlist-ID scans.

## Next Step

- Refresh the compact cross-band verification summary so `um` and `eggy` move out of review status and the remaining open work, if any, is based on current evidence rather than stale diagnostics.
