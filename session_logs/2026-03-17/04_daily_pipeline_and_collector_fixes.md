# Daily Pipeline and Collector Fixes

## Goal

- Ensure all GitHub Actions are running properly.
- Investigate and resolve the cause of the `billy` pipeline taking 14+ minutes to execute compared to other bands.

## Constraints

- Fix pipeline workflow definitions safely without degrading coverage.
- Preserve existing iterative collector schemas.

## Commands Run

```bash
gh run list --limit 10
gh workflow run daily-pipeline.yml --ref streamlined
gh run view 23210853722
gh run view --job=67291644618 --log
uv run pytest -q
```

## Files Changed

- `.github/workflows/daily-pipeline.yml`: Fixed invalid `secrets` context in job-level `if` condition. Moved it to step level using `env`.
- `tests/test_db.py`: Fixed `test_get_supabase_client_success` which was failing due to state carryover from the module's `_supabase_client` singleton.
- `scripts/run_billy_collection.py`: Replaced raw `.execute()` limit queries with `fetch_table` to bypass Supabase's 1000 row cap and prevent the script from redundantly re-scraping existing setlists.
- `src/jambandnerd/data_collection/wsp/orchestration.py`: Applied the same `fetch_table` fix to WSP.
- `src/jambandnerd/data_collection/billy/collector.py`: Appended a trailing slash to the `https://bmfsdb.com/songs/` endpoint to prevent the server from redirecting to port 8080 and causing a 120-second timeout across 5 retries.
- `.agent/PLAYBOOK.md`: Added durable lessons about pagination limits and trailing slashes for iterative collectors.

## Validation Status

- Validated `.github/workflows/daily-pipeline.yml` run `23210853722` and confirmed all jobs (`setup`, `um`, `goose`, `phish`, `wsp`, `eggy`) succeeded successfully.
- Validated `uv run pytest -q` and confirmed all 127 tests passed locally after the singleton teardown fix.
- Confirmed the fix for the Billy Strings data collector addresses the 10-minute port 8080 hang and the ~3-minute un-paginated setlist checking penalty.

## Next Step

- Let the daily pipeline run successfully on schedule. Review predictions output for all bands on the Streamlit UI.