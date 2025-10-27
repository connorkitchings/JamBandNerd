# Adding Eggy & Cosmic Country Support

This guide captures the implementation plan for onboarding **Eggy** and **Daniel Donato’s Cosmic Country** into the JamBandNerd data pipeline and prediction suite.

---

## 1. Goals & Scope
- Ingest shows, setlists, songs, and venues for both bands into Supabase raw tables.
- Feed the new data through existing transformations, models, prediction storage, and accuracy reporting.
- Update the CLI tools, orchestrated pipeline, and Streamlit UI so the bands behave like existing options (Goose, Phish, WSP, Billy, UM).
- Provide validation, documentation, and lightweight tests that keep the pipeline reliable.

---

## 2. Source Mapping & Schema Alignment

### Eggy (thecarton.net API)
- REST JSON endpoints: `/api/v2/shows.json`, `/api/v2/setlists.json`, `/api/v2/songs.json`, `/api/v2/venues.json`.
- Response shape closely mirrors Goose, so mapping to `eggy_*_raw` tables will follow Goose normalization logic (string IDs, ISO date parsing, source hashes).
- Confirm Supabase has raw tables or generate DDL mirroring Goose tables with an `eggy_` prefix.

### Cosmic Country (danielbase.com)
- HTML UI rendered via PrimeFaces; requires scraping similar to WSP/Billy collectors.
- Need robust parsing for show listings, per-show setlists, segue markers (`>`, `,`), and footnotes.
- Plan Supabase tables (`cosmic_shows_raw`, `cosmic_setlists_raw`, etc.) aligned with Billy/WSP schemas.

---

## 3. Ingestion Implementation

### 3.1 Eggy Collector
1. Create `src/jambandnerd/data_collection/eggy/collector.py` mirroring Goose (rate limiting, API fetch helper).
2. Implement `collect_shows`, `collect_setlists`, `collect_songs`, and `collect_venues`, filtering on `artist="Eggy"`.
3. Build `scripts/run_eggy_collection.py`:
   - Normalize API payloads into Pandas DataFrames (dates, encore flags, source hashes).
   - Upsert into Supabase via `upsert_dataframe`, ensuring column coercion/validation.
4. Thread into `scripts/run_optimized_pipeline.py` and any band registries (CLI choices, config).

### 3.2 Cosmic Country Collector
1. Add `src/jambandnerd/data_collection/cosmic/collector.py` that:
   - Scrapes the search UI for show listings (pagination or filter by year).
   - Fetches individual show pages, parses setlists, handles segues/encores/notes.
   - Builds resilient error handling (timeouts, retries, optional tqdm progress) similar to WSP/Billy.
2. Implement `scripts/run_cosmic_collection.py` handling normalization, Supabase upserts, and de-duplication.
3. Consider helper utilities (regex cleanup, tooltip extraction) tucked inside the collector module for readability.

### 3.3 Configuration & Utilities
- Extend `src/jambandnerd/data_collection/config.py` with collector configs (base URL, rate limits).
- Register new collectors in any lookup tables (e.g., `data_collection/collect_data.py` manager, pipeline orchestrator).
- Update `ensure_source_reachable` expectations if endpoints require special paths or headers.

---

## 4. Pipeline & Modeling Integration
- Update `SUPPORTED_BANDS`, display names, ID columns, retirement gaps, and exclusion lists in `src/jambandnerd/config.py`.
- Allow `generate_predictions.py`, `run_backtest.py`, `save_aggregate_accuracy.py`, and validation scripts to accept `eggy` and `cosmic`.
- Create or refresh Supabase prediction/accuracy rows once collectors populate raw tables.
- Ensure Streamlit band dropdowns and Supabase queries include the new entries.

---

## 5. Testing & Validation
- Add smoke/unit tests for the new collectors (e.g., fixture HTML/JSON snippets) under `tests/`.
- Run notebook/CK+ prediction flows locally after seeding a sample dataset; capture any data anomalies (missing shows, off-by-one gaps).
- Update validation scripts to recognize the new raw tables (schema lookups, table fetch helpers).

---

## 6. Documentation Deliverables
- Draft schema notes or append to existing references (`docs/reference/schemas/`) describing Eggy API mappings and Cosmic Country scrape fields.
- Extend README or architecture docs with brief mention of new support once implemented.
- Log Supabase table DDL changes or migrations in the internal runbook (if required).

---

## 7. Rollout Checklist
1. ✅ Health-check endpoints (`ensure_source_reachable`) for both sources.
2. ✅ Collector modules and run scripts merged.
3. ✅ Config/pipeline updates deployed.
4. ✅ Raw tables confirmed populated in Supabase.
5. ✅ Predictions/backtests executed for a smoke test.
6. ✅ Streamlit UI verified with new bands.
7. ✅ Docs & tests merged; optional backfill jobs scheduled.

Following this plan keeps the new bands aligned with existing architecture while minimizing bespoke logic. Update this guide as implementation details evolve.

