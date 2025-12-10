# Session Log: Last Show Analysis Bug Fixes & WSP Collection Repair

**Date:** 2025-12-10
**Duration:** ~100 minutes

---

## 📋 Task Completed

Fix invalid input syntax error and missing data issues in WSP Show upsert process. Ensure "Last Show Analysis" displays correct November 2025 data.

## 🔑 Key Outcomes

### 1. Fixed "Invalid Input Syntax" for Show IDs

- **Issue:** `WSPCollector` generated alphanumeric show IDs (e.g., "20250214a") which clashed with the integer `show_id` column in `wsp_shows_raw`.
- **Fix:** Updated `orchestration.py` to:
  - Fetch existing shows from DB to reuse IDs.
  - Query the max `show_id` from DB.
  - Assign sequential integer IDs to new shows.

### 2. Resolved WSP Collection Failures (Missing Nov 2025 Shows)

- **Issue:** `WSPCollector` failed to parse tour pages (due to GZIP encoding issues) and failed to upsert setlists (due to mismatched keys and NULL timestamps).
- **Fixes:**
  - **Session:** Removed `Accept-Encoding` header to enable automatic decompression.
  - **Encoding:** Forced `Windows-1252` encoding for EverydayCompanion responses.
  - **Normalizer:** Updated `normalize_shows` and `normalize_setlists` to support EC collector keys and derive/map fields correctly.
  - **Database:** Updated `upsert_dataframe` to filter out `None` values for `created_at`/`updated_at`, allowing DB defaults to apply and preventing NOT-NULL violations.

### 3. Duplicate Setlist Songs Resolved

- **Issue:** UI displayed duplicate songs in setlists.
- **Fix:** Removed 231 invalid rows with negative song positions from DB and added deduplication logic in UI/Data layers.

### 4. Date Off-by-One Fixed in Charts

- **Issue:** Model Performance tooltips showed -1 day offset.
- **Fix:** Added explicit string formatting for dates in Altair charts.

### 5. Fixed CI Pipeline Failures (403s & Threading)

- **Issue:** GitHub Actions pipeline failed due to:
  1.  **403 Forbidden:** TourWrangler/scraper blocked Headless Chrome (even with Playwright).
  2.  **Threading Error:** `ThreadPoolExecutor` clashed with Playwright (not thread-safe).
  3.  **User-Agent Mismatch:** Chrome UA on Firefox browser triggered WAFs.
- **Fix:**
  - **Browser:** Switched to **Headless Firefox** in `session.py`.
  - **Identity:** Aligned User-Agent and injected standard headers (`Referer`, etc.).
  - **Concurrency:** Implemented sequential execution for setlist collection in CI environments (`collector.py`).

## 🚧 Blockers Encountered

- **Schema Mismatch:** The Normalizer (built for TourWrangler) and Collector (EC scraper) had completely different key names (`setnumber` vs `set_number`, etc.), causing silent data drops.
- **CI-Specific WAFs:** Aggressive blocking of Headless Chrome required switching to Firefox and fine-tuning headers.

## 🔄 Session Handoff & Next Steps

**Immediate Next Task:** Monitor the next scheduled Daily Pipeline run to ensure long-term stability.

**Updated Documents:**

- `src/jambandnerd/data_collection/wsp/session.py`
- `src/jambandnerd/data_collection/wsp/collector.py`
- `src/jambandnerd/data_collection/wsp/orchestration.py`
- `src/jambandnerd/data_collection/wsp/normalizer.py`
- `src/jambandnerd/db/operations.py`
- `src/jambandnerd/web/components/tabs/last_show.py`
- `src/jambandnerd/web/components/tabs/performance.py`
- `tests/web/test_data_quality.py`
- `.github/workflows/daily-pipeline.yml`
