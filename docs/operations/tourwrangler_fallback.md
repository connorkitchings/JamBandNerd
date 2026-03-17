# TourWrangler Fallback for WSP

This guide documents the backup data-reader for Widespread Panic (WSP) using TourWrangler when Everyday Companion (EC) lacks a recent historical setlist.

## When It Runs

- Triggered during WSP collection after EC upserts finish.
- Checks the last N days (default 3, excluding today) for shows that have no setlist rows in the database.
- For each such show, attempts to parse TourWrangler and upsert setlist rows.

Configure the window via environment variable:

- WSP_BACKUP_WINDOW_DAYS (default: 3)

## Parser Behavior

- Strictly parses content within "Set 1", "Set 2", and "Encore" sections.
- Trims at page-level stop-words (e.g., "Liner Notes", "Videos", "More by", "You might also like").
- Removes artist-credit markers appended after songs (e.g., Widespread Panic, Junior Kimbrough, Drivin’ n’ Cryin’, Warren Zevon, brute., Talking Heads, Buffalo Springfield).
- Removes bracketed footnotes like "[ 1 ]" and stray bracket tokens.
- Drops non-song tokens (pure years, month-day ordinals like "September 21st", punctuation-only, UI voice like "Stream").
- Preserves segues using ">" splitting after cleanup.

Known source discrepancy (accepted):

- 2025-10-03 Encore: TourWrangler omits "Sewing Machine" while EC includes it.

## EC-over-TW Promotion (Preferred Data)

To automatically replace TW rows with EC rows when EC becomes available:

1) Add the `source` column to `wsp_setlists_raw`:

```sql
ALTER TABLE public.wsp_setlists_raw ADD COLUMN IF NOT EXISTS source text;
```

2) Re-run the WSP collection:
- EC upserts will tag rows with `source='everydaycompanion'` (the code auto-populates when the column exists)
- The EC-over-TW promotion step will then delete `source='tourwrangler'` rows for recent shows covered by EC

Safety net without `source` column:
- The collection script performs a structural cleanup for recent shows by removing any rows not present in EC (by set_number + song_position). This is less precise than using the `source` column and is intended as a stopgap.

## EC Show Identity

- For `wsp_shows_raw`, the canonical Everyday Companion identity is `source_url`.
- The collector now reuses `show_id` by exact `source_url` match before falling back to `(show_date, normalized venue_name)`.
- Venue labels can drift on EC, so `show_date + venue_name` is only a secondary reconciliation key.
- If WSP collection fails on a duplicate `source_url`, treat it as a show-identity regression in the EC reconciliation path rather than a generic upsert problem.

## Operational Tips

- To extend the detection window, set `WSP_BACKUP_WINDOW_DAYS` in your environment.
- If both TW and EC are missing, the show remains without a setlist in the DB.
- The parser is resilient to formatting variations and site chrome but errs on removing anything that looks like metadata.

## Testing Utilities

- `scripts/manual/wsp/tw_compare_ec_tw.py`
  - Compares EC rows (from DB or prior backup) with a parsed TourWrangler URL for a specific date.
- `scripts/manual/wsp/tw_fallback_test.py`
  - Backs up and temporarily deletes setlist rows for specified dates, upserts TourWrangler rows, and prints a diff vs the backup.
