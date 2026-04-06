# Fixes 2 & 4: Prediction Storage Cleanup + WSP Parser Versioning

**Date**: 2026-04-06
**Branches**: `fix/prediction-storage-cleanup`, `fix/wsp-parser-versioning` → merged to `dev`

---

## Fix 2: Prediction Storage Cleanup

### Changes

- **`src/jambandnerd/db/operations.py`**: Added `_cleanup_stale_prediction_songs()` — deletes `prediction_songs` rows older than 30 days per band/model_version, with a safety guard that never deletes the most recent `reference_date`. Called automatically at the end of `replace_prediction_projection()`. Updated docstring on `replace_prediction_projection()` to document the dual-write pattern.
- **`scripts/rebuild_prediction_songs.py`**: New rebuild script — reads canonical prediction tables, parses the JSONB blob, and calls `replace_prediction_projection()` for each band/model. Supports `--band` and `--model` filters.
- **`scripts/validate_prediction_tables.py`**: Added `_check_stale_projection_rows()` — queries `prediction_songs` for distinct `(band, model_version, reference_date)` tuples and flags any older than `max_age_hours`.
- **`scripts/generate_predictions.py`**: Added comment block documenting the two-step write sequence.
- **`tests/test_db_operations.py`**: Updated `_QueryStub` with `select`, `order`, `limit`, `lt`, `neq` methods to support the cleanup function.

### Verification

- `uv run black src tests scripts` — clean
- `uv run ruff check src tests scripts` — clean
- `uv run pytest` — 170 passed, 6 skipped, 1 pre-existing failure (unrelated)

---

## Fix 4: WSP Scraper Versioning

### Changes

- **`src/jambandnerd/data_collection/wsp/parser_profile.py`**: New module with `ParserProfile` dataclass (versioned DOM assumptions), `DEFAULT_PROFILE` instance, `fingerprint_page()` and `validate_fingerprint()` helpers.
- **`src/jambandnerd/data_collection/wsp/collector.py`**: Replaced hardcoded `tables[4]`, `tables[4:8]`, `len(tables) < 5`, and string-based link matching with `DEFAULT_PROFILE` fields. Added fingerprint logging on setlist pages.
- **`src/jambandnerd/data_collection/wsp/songs.py`**: Same profile-based replacements for song catalog parsing.
- **`src/jambandnerd/data_collection/wsp/shows.py`**: Same profile-based replacements for tour page link matching.
- **`src/jambandnerd/data_collection/wsp/orchestration.py`**: Updated `_page_has_setlist_table()` to use profile fields and added fingerprint check with structured warning logging.
- **`tests/data_collection/wsp/fixtures/`**: Three HTML fixture files (`song_catalog.html`, `setlist_page.html`, `tour_page.html`).
- **`tests/data_collection/wsp/test_wsp_html_parsing.py`**: Five pure regression tests — song catalog parsing, setlist parsing, tour page link extraction, fingerprint matching, and layout-change detection.

### Verification

- `uv run black src tests scripts` — clean
- `uv run ruff check src tests scripts` — clean
- `uv run pytest` — 170 passed (including 5 new), 6 skipped, 1 pre-existing failure

---

## Remaining

- **Fix 3 (Unify Phish `show_id`)**: High-risk — requires coordinated Supabase migration. Deferred pending user coordination.
