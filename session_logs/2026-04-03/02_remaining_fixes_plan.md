# Remaining Fixes Plan

**Date**: 2026-04-03
**Status**: Planned, not yet implemented
**Context**: Comprehensive repo review identified 4 technical debt items. Fix 1 (admin auth gating) shipped in `01_admin_auth_gating.md`. This log documents the implementation plans for Fixes 2–4.

---

## Fix 2: Hybrid Prediction Storage Cleanup

**Branch**: `fix/prediction-storage-cleanup`
**Risk**: Low-Medium

### Problem
The system dual-writes predictions: a canonical JSON run row (`predictions_notebook` / `predictions_ckplus`) and a derived per-song projection (`prediction_songs`). The website reads exclusively from `prediction_songs`. Two gaps exist:
1. No stale-row cleanup — old `reference_date` rows accumulate in `prediction_songs` indefinitely
2. No rebuild path — if `prediction_songs` is corrupted or truncated there is no documented recovery

### Implementation

**1. Add stale-row cleanup** — `src/jambandnerd/db/operations.py`

After the existing delete-then-insert in `replace_prediction_projection()` (lines 264–303), call a new helper `_cleanup_stale_prediction_songs()`:
- Delete rows in `prediction_songs` where `reference_date < (today - 30 days)` for the given `band` + `model_version`
- Safety guard: NEVER delete the most recent `reference_date` row (query for max before deleting)
- Log the count of cleaned rows

**2. Create rebuild script** — NEW `scripts/rebuild_prediction_songs.py`

```
Usage: uv run python scripts/rebuild_prediction_songs.py [--band BAND] [--model MODEL]
       (omit both flags to rebuild all)
```

For each band/model:
1. Query canonical table (`predictions_notebook` or `predictions_ckplus`) for the latest row by `predicted_at`
2. Parse the JSONB `predictions` blob with `serialize_model_predictions()` from `models/registry.py`
3. Call `replace_prediction_projection()` from `db/operations.py`
4. Print a per-band summary

Follow the pattern of `scripts/validate_prediction_tables.py`. Use `list_pipeline_models()` from `models/registry.py` to enumerate models.

**3. Add stale-row detection** — `scripts/validate_prediction_tables.py`

In the existing `validate_predictions()` function, add a new check:
- Query `prediction_songs` for distinct `(band, model_version, reference_date)` tuples
- Flag any `reference_date` older than `max_age_hours` (already a parameter on the function)
- Increment `failures` counter and report stale rows in output

**4. Document the dual-write pattern**

Add docstring to `replace_prediction_projection()` in `operations.py` explaining:
- `prediction_songs` is a derived projection of the canonical tables
- It is fully rebuildable via `scripts/rebuild_prediction_songs.py`
- The delete-then-insert pattern prevents stale rows for the *current* reference_date but does not clean older dates (handled by the cleanup step)

Add a comment block in `scripts/generate_predictions.py` near lines 159–171 describing the two-step write sequence.

### Verification

```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/rebuild_prediction_songs.py --band goose --model notebook
```

---

## Fix 3: Unify Phish show_id

**Branch**: `fix/unify-phish-show-id`
**Risk**: High — live Supabase schema migration

### Problem
Phish raw tables use `api_show_id` (bigint) as the show primary key while every other band uses `show_id` (varchar). The aliasing is handled at the normalization boundary, but `api_show_id` leaks into four places outside that boundary:
- `scripts/run_phish_collection.py` — column mapping and conflict key
- `scripts/run_live_tracker.py` line 134 — hardcoded `if band == "phish"` check
- `scripts/get_last_completed_show_date.py` line 26 — same hardcoded check
- `src/jambandnerd/config/bands.py` `BAND_ID_COLUMNS` — Phish exception

### Deployment Order

**Deploy code changes first**, then run the Supabase migration. The normalization layer already accepts both `show_id` and `api_show_id` as fallback candidates, so the pipeline is safe to deploy before the DB column rename. Run migration only after verifying the deployed code passes tests.

### Implementation

**1. Supabase migration** — NEW `supabase/migrations/20260403_unify_phish_show_id.sql`

```sql
-- Rename api_show_id to show_id in Phish raw tables
ALTER TABLE phish_shows_raw RENAME COLUMN api_show_id TO show_id;
ALTER TABLE phish_setlists_raw RENAME COLUMN api_show_id TO show_id;

-- Rename affected indexes/constraints (inspect actual names first with
-- SELECT indexname FROM pg_indexes WHERE tablename = 'phish_shows_raw')

-- Update band registry
UPDATE bands SET id_column = 'show_id' WHERE slug = 'phish';
```

Before writing the final migration, inspect the actual constraint names:
```sql
SELECT indexname FROM pg_indexes WHERE tablename IN ('phish_shows_raw', 'phish_setlists_raw');
SELECT conname FROM pg_constraint WHERE conrelid = 'phish_shows_raw'::regclass;
```

**2. Update config** — `src/jambandnerd/config/bands.py`

Line 32: `"phish": "api_show_id"` → `"phish": "show_id"`

After this change all values in `BAND_ID_COLUMNS` are `"show_id"`. Consider simplifying `get_band_id_column()` to just return `"show_id"` unconditionally, or keep the dict for future bands that may differ.

**3. Update Phish collection** — `scripts/run_phish_collection.py`

- `_normalize_shows()`: `"api_show_id": item.get("showid")` → `"show_id": item.get("showid")`
- `_normalize_setlists()`: same rename
- Line 306: `conflict_columns=["api_show_id"]` → `conflict_columns=["show_id"]`
- Line 317: `filtered_shows_df["api_show_id"]` → `filtered_shows_df["show_id"]`

**4. Remove hardcoded Phish checks**

`scripts/run_live_tracker.py` line 134:
```python
# Remove: if band == "phish": show_id_col = "api_show_id" else: show_id_col = "show_id"
show_id_col = "show_id"
```

`scripts/get_last_completed_show_date.py` line 26:
```python
# Remove: id_col = "api_show_id" if band == "phish" else "show_id"
id_col = "show_id"
```

**5. Simplify normalization** — `src/jambandnerd/transformations/normalization.py`

Keep `"api_show_id"` in the `show_id_candidates` fallback list for now (backward-compat during the migration window). Remove it in a follow-up commit after verifying production migration succeeded.

**6. Update tests**

`tests/pipeline/fixtures.py`: remove the `api_show_id` / `show_id` conditional for Phish; use `"show_id"` unconditionally.

`tests/pipeline/test_normalization_contract.py`: update Phish test DataFrame to use `show_id` as input column. Optionally add a separate backward-compat test that verifies `api_show_id` still aliases correctly (using the fallback in candidates list).

**Note**: Other `api_*` columns in the Phish raw tables (`api_song_id`, `api_venue_id`, `api_unique_id`, etc.) are intentionally left unchanged — they do not cross the normalization boundary and are internal to the Phish collector.

### Verification

```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest

# After migration applied:
uv run python scripts/get_last_completed_show_date.py --band phish
uv run python scripts/run_optimized_pipeline.py --band phish --skip-accuracy
```

---

## Fix 4: WSP Scraper Versioning

**Branch**: `fix/wsp-parser-versioning`
**Risk**: Low — purely additive

### Problem
All DOM assumptions in the WSP collector are hardcoded positional values (`tables[4]`, `tables[4:8]`) and content heuristics (`"1:"`, `"setlist"`). When Everyday Companion changes its HTML structure, parsing fails silently — most errors are swallowed, counters eventually flag the run as degraded, but the root cause is not surfaced. There are zero HTML fixture tests; `BeautifulSoup` is always mocked.

### Implementation

**1. Create ParserProfile dataclass** — NEW `src/jambandnerd/data_collection/wsp/parser_profile.py`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ParserProfile:
    """Versioned DOM assumptions for everydaycompanion.com parsing.

    Update `version` and the relevant field(s) whenever the site structure
    changes. Keep old profiles in this file for historical reference.
    """
    version: str = "2026-04-03"

    # Song catalog page (/asp/songcode.asp)
    song_table_index: int = 4
    song_table_min_tables: int = 5
    song_table_columns: tuple[str, ...] = (
        "code", "song_name", "first_played", "last_played", "times_played", "aka"
    )

    # Setlist page (individual show pages)
    setlist_table_range: tuple[int, int] = (4, 8)
    setlist_set_markers: tuple[str, ...] = ("0:", "1:", "2:", "3:", "E:")
    setlist_noise_markers: tuple[str, ...] = ("Song Stats",)

    # Tour index pages (/asp/tourYY.asp)
    tour_link_extension: str = ".asp"
    tour_link_href_patterns: tuple[str, ...] = ("setlist", "/setlists/")


DEFAULT_PROFILE = ParserProfile()


def fingerprint_page(soup, profile: ParserProfile) -> dict:
    """Return structural metadata about the page for validation."""
    tables = soup.find_all("table")
    text = soup.get_text()
    return {
        "table_count": len(tables),
        "has_set_markers": any(m in text for m in profile.setlist_set_markers),
        "has_song_catalog_table": len(tables) > profile.song_table_index,
        "has_tour_links": any(
            p in (a.get("href", "") or "") for a in soup.find_all("a")
            for p in profile.tour_link_href_patterns
        ),
    }


def validate_fingerprint(fingerprint: dict, profile: ParserProfile) -> list[str]:
    """Return a list of warnings if the page structure does not match expectations."""
    warnings = []
    if fingerprint["table_count"] < profile.song_table_min_tables:
        warnings.append(
            f"Expected >= {profile.song_table_min_tables} tables, found {fingerprint['table_count']}"
        )
    return warnings
```

**2. Integrate into collector.py** — `src/jambandnerd/data_collection/wsp/collector.py`

- Import `DEFAULT_PROFILE`, `fingerprint_page`, `validate_fingerprint` from `parser_profile`
- Replace `tables[4]` → `tables[profile.song_table_index]`
- Replace `len(tables) < 5` → `len(tables) < profile.song_table_min_tables`
- Replace `tables[4:8]` → `tables[profile.setlist_table_range[0]:profile.setlist_table_range[1]]`
- Replace hardcoded `"setlist" in href or "/setlists/" in href` → check against `profile.tour_link_href_patterns`
- Add fingerprint check before table parsing:
  ```python
  fp = fingerprint_page(soup, DEFAULT_PROFILE)
  warnings = validate_fingerprint(fp, DEFAULT_PROFILE)
  if warnings:
      logger.warning("WSP DOM fingerprint mismatch: %s", "; ".join(warnings))
  ```

**3. Same integration into songs.py and shows.py**

These files duplicate the table-index and link-pattern logic from `collector.py`. Apply the same profile-based replacements.

**4. Add fingerprint check to orchestration.py**

In `_page_has_setlist_table()` (line 42 area), add `fingerprint_page()` + `validate_fingerprint()` call before the table search. Log warnings as structured output so they are visible in CI degraded-mode reports.

**5. Create HTML fixture files** — NEW `tests/data_collection/wsp/fixtures/`

Three files, constructed to match the real EC DOM structure:
- `tour_page.html` — tour index with `<a>` links containing `"setlist"` in href, date-formatted link text
- `setlist_page.html` — show page with 8+ tables, set marker text (`"1:"`, `"2:"`, `"E:"`), comma-separated songs
- `song_catalog.html` — song code page with 5+ tables, 6-column catalog at index 4

These serve as regression anchors. If the site changes, the fixtures represent the last known-good structure.

**6. Write fixture-based regression tests** — NEW `tests/data_collection/wsp/test_wsp_html_parsing.py`

```python
# Tests (all pure — no network, no DB):
test_parse_song_catalog_from_fixture()      # verify 6 columns, at least 1 row
test_parse_setlist_from_fixture()           # verify songs extracted per set
test_parse_tour_page_from_fixture()         # verify show links found with dates
test_fingerprint_matches_default_profile()  # no warnings on valid HTML
test_fingerprint_detects_layout_change()    # warnings when tables removed
```

Load fixtures via `pathlib.Path(__file__).parent / "fixtures" / "filename.html"`.

### Verification

```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest tests/data_collection/wsp/   # fixture tests are pure, no network
uv run pytest                               # full suite
```

---

## Shared Notes

- Each fix gets its own branch off `dev`
- Run quality gates before merging: `uv run black src tests scripts && uv run ruff check src tests scripts && uv run pytest`
- Fix 3 (Phish show_id) is the highest-risk item; coordinate the migration window to avoid a pipeline run between code deploy and migration apply
- Fix 2 and Fix 4 are fully safe to ship independently at any time
