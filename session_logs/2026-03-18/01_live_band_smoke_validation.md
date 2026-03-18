# Live Band Smoke Validation

## Goal

- Validate the newly added per-band live smoke suite against real upstreams and Supabase publishing paths.
- Confirm the recent collector fixes for WSP and Billy hold up in end-to-end execution.

## Constraints

- Keep the live runs attributable by executing one band at a time.
- Reuse the new `@pytest.mark.live` path instead of ad hoc manual commands.

## Commands Run

```bash
set -a; source .env; set +a; uv run pytest -q -m live tests/pipeline/test_live_band_smoke.py -k wsp
set -a; source .env; set +a; uv run pytest -q -m live tests/pipeline/test_live_band_smoke.py -k billy
set -a; source .env; set +a; uv run pytest -q -m live tests/pipeline/test_live_band_smoke.py -k goose
set -a; source .env; set +a; uv run pytest -q -m live tests/pipeline/test_live_band_smoke.py -k eggy
set -a; source .env; set +a; uv run pytest -q -m live tests/pipeline/test_live_band_smoke.py -k phish
set -a; source .env; set +a; uv run pytest -q -m live tests/pipeline/test_live_band_smoke.py -k um
```

## Files Changed

- `tests/pipeline/test_live_band_smoke.py`: exercised live full-pipeline validation band by band.
- `tests/pipeline/live_helpers.py`: verified fresh prediction and accuracy publishes after each run.
- `.agent/PLAYBOOK.md`: added a note about exporting `.env` before env-gated live pytest runs.

## Validation Status

- WSP live smoke passed in 64.84s.
- Billy live smoke passed in 44.08s.
- Goose live smoke passed in 18.51s.
- Eggy live smoke passed in 17.53s.
- Phish live smoke passed in 55.71s.
- UM live smoke passed in 46.63s.
- All six runs confirmed fresh `predictions_notebook`, `predictions_ckplus`, `accuracy_per_show`, and aggregate accuracy rows for the band under test.
- No band-specific failures were observed during ingestion, transformation, or publishing.

## Notes

- Each live pytest invocation emitted the same Supabase client deprecation warnings for `timeout` and `verify`; these are non-blocking but worth cleaning up separately.
- The live suite requires environment variables to be exported before pytest starts; a plain `.env` file is not enough for the `ensure_live_env()` preflight check by itself.

## Next Step

- Review the final diff, then commit the new pipeline tests, live smoke coverage, and session artifacts together.
