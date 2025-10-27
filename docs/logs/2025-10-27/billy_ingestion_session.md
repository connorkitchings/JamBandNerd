# JamBandNerd Session Log — Billy Strings Ingestion

**Date:** 2025-10-27  
**Focus:** Extend raw data pipeline to ingest Billy Strings shows & setlists.

## Progress
- Implemented full bmfsdb scraper (`scripts/run_billy_collection.py`, `src/jambandnerd/data_collection/billy/collector.py`) and wired it into the orchestrator/prediction tooling.
- Added Supabase schema via migration `create_billy_raw_tables` (`billy_shows_raw`, `billy_setlists_raw`).
- Attempted local ingestion run; blocked because the venv cannot install project dependencies.

## Current Blocker
- `pip install -e .` fails: macOS reports `SSLCertVerificationError (OSStatus -26276)` for every request to PyPI, so `setuptools>=61` (and other deps) never download.
- Without project deps in `.venv`, running the collector raises `ModuleNotFoundError: No module named 'src'`.

## Next Steps
1. Repair Python SSL trust (e.g., run “Install Certificates.command” or otherwise restore CA bundle) so pip can talk to PyPI.
2. Re-run inside the venv: `python -m pip install --upgrade pip setuptools` → `python -m pip install -e .`.
3. Execute the collector: `python scripts/run_billy_collection.py --start-date 2024-01-01 --skip-validation`.
4. Verify Supabase tables have populated rows and continue with prediction/backtest integration.

## Notes
- Raw tables already exist; once dependencies install cleanly, ingestion should succeed without further code changes.
