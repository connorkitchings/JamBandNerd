# WSP Ingestion Fix

## Goal

- Fix the WSP ingestion failure caused by duplicate `source_url` collisions in `wsp_shows_raw`, then verify the downstream prediction path still works.

## Constraints

- Keep `show_id` as the application-facing join key.
- Do not rely on venue text as the primary EC show identity.
- Avoid broad unrelated changes in an already-dirty worktree.

## Commands Run

```bash
uv run pytest tests/data_collection/test_wsp_normalization.py tests/data_collection/test_wsp_orchestration.py tests/data_collection/test_wsp_collector.py -q
uv run python -m py_compile src/jambandnerd/data_collection/wsp/orchestration.py src/jambandnerd/data_collection/wsp/normalizer.py
PYTHONUNBUFFERED=1 uv run python scripts/run_wsp_collection.py
uv run python scripts/generate_predictions.py --band wsp --model notebook
uv run python scripts/generate_predictions.py --band wsp --model ckplus
uv run python scripts/validate_prediction_tables.py --band wsp --max-age-hours 2
BAND=wsp uv run python scripts/verify_data_freshness.py
curl -sS https://raw.githubusercontent.com/connorkitchings/panicstats/main/docs/legal/data_source_policy.md
curl -sS https://raw.githubusercontent.com/connorkitchings/panicstats/main/docs/architecture/system_overview.md
```

## Files And Artifacts

- `src/jambandnerd/data_collection/wsp/orchestration.py`: reconcile EC shows by `source_url` first, dedupe batches, and fail early on ambiguous identity.
- `src/jambandnerd/data_collection/wsp/normalizer.py`: require orchestration-assigned `show_id` for show rows and drop invalid setlist positions.
- `tests/data_collection/test_wsp_orchestration.py`: regression coverage for source-url reuse, venue drift, and fallback matching.
- `tests/data_collection/test_wsp_normalization.py`: regression coverage for missing `show_id` and invalid setlist positions.
- `docs/operations/tourwrangler_fallback.md`: operational note that `source_url` is the canonical EC identity.

## Validation

- WSP collector now exits `0` live against Supabase and logs `reused_by_source_url=57`, `new_ids=0`.
- The previously failing EC URL `https://www.everydaycompanion.com/setlists/20260214a.asp` now reuses its existing `show_id` instead of triggering `wsp_shows_raw_source_url_key`.
- `generate_predictions.py` passed for WSP `notebook` and `ckplus`.
- `validate_prediction_tables.py --band wsp --max-age-hours 2` passed for both prediction tables.
- `verify_data_freshness.py` reported no recent WSP shows in the last 7 days, so no freshness gap remains.
- PanicStats does not provide an EC ingestion implementation to port; its public docs treat Everyday Companion as prohibited for automated ingestion and reference-only.

## Next Step

- Apply the same “latest by `predicted_at`” fix to `scripts/validate_prediction_tables.py` so future cross-band verification does not report false stale rows.
