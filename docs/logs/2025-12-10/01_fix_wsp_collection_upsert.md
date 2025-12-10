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

## 🚧 Blockers Encountered

- **Schema Mismatch:** The Normalizer (built for TourWrangler) and Collector (EC scraper) had completely different key names (`setnumber` vs `set_number`, etc.), causing silent data drops.
- **UnboundLocalError:** Minor scope issue in orchestration script during rapid iteration (fixed).

## 🔄 Session Handoff & Next Steps

**Immediate Next Task:** verify the GitHub Actions "Daily Pipeline" run.

- **Note:** We deleted the Nov 23, 2025 show from the DB to verify that the pipeline correctly re-collects it.

**Updated Documents:**

- `src/jambandnerd/data_collection/wsp/session.py`
- `src/jambandnerd/data_collection/wsp/collector.py`
- `src/jambandnerd/data_collection/wsp/orchestration.py`
- `src/jambandnerd/data_collection/wsp/normalizer.py`
- `src/jambandnerd/db/operations.py`
- `src/jambandnerd/web/components/tabs/last_show.py`
- `src/jambandnerd/web/components/tabs/performance.py`
- `tests/web/test_data_quality.py`

## 🚨 Post-Closure Update (CI Pipeline Fix)

After closing the session, we identified that the **GitHub Actions pipeline failed** to collect setlists, despite the local fix working.

- **Root Cause:** In CI environments, `WSPCollector` uses Playwright to bypass bot detection. Playwright returns a mock `requests.Response` object with `utf-8` encoded content. Our previous fix (Step 2 above) blindly forced `response.encoding = "windows-1252"`, which caused the UTF-8 content to be re-decoded incorrectly (Mojibake), corrupting the HTML.
- **Fix:** Updated `decode_ec_response` in `session.py` to check for `response.encoding == "utf-8"` (set by Playwright) and return the text as-is in that case.
- **Verification:** Verified code logic. User instructed to re-run pipeline.

### UPDATE 2: 403 Forbidden & Threading Issues in CI

A second attempt revealed two more CI-specific issues:

- **403 Forbidden on Show Collection:** `make_simple_request` (used for tour pages) was using standard `requests`, which got blocked. Fixed by using Playwright for these requests in CI (`session.py`).
- **Greenlet/Threading Error:** `Cannot switch to a different thread`. Caused by `WSPCollector` using `ThreadPoolExecutor`, which tried to access the main-thread-bound Playwright object from worker threads. Fixed by forcing sequential execution in CI (`collector.py`).

### UPDATE 3: Persistent 403s (Switching to Firefox)

The "Round 2" fix used Headless Chrome, which **still received 403 Forbidden errors** for tour pages.

- **Strategy Change:** Switched `session.py` and GitHub Actions workflow to use **Headless Firefox** instead of Chromium. Firefox often successfully bypasses anti-bot protections that target headless Chrome signatures.

### UPDATE 4: UA/Browser Mismatch (Attempt 3 Failed)

Attempt 3 (Firefox) also failed with 403s.

- **Root Cause:** We switched to Firefox but **left the User-Agent as Chrome**. This mismatch (Firefox browser engine + Chrome UA) is a huge red flag for WAFs.
- **Fix:** Updated `session.py` to use a genuine Firefox User-Agent string and inject standard headers (`Referer`, `Accept`, etc.) into the Playwright context to mimic a real user session.
