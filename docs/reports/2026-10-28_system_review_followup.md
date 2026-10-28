# 2026-10-28 System Review Follow-up: Duplicate Shows, Billy Gaps and Cleanup

This report records what was fixed and cleaned up after the 2026-10-27 review, and what is still open. The larger deferred items are in `docs/reports/2026-10-27_system_review.md`. The session log is `session_logs/2026-10-27/02.md`.

Terms used below: a **ghost row** is a show row with 0 songs. A **duplicate pair** is two show rows for the same show, both with full setlists. A **phantom row** is a show row for a date that was postponed or never happened.

## Summary

- Umphreys had duplicate and ghost show rows since about 2026-05-10, when the source site changed its URL format. All were removed, and the collector fix (#225) prevents new ones.
- The Umphreys duplicates shifted the 50-show window that the model uses. Only 69% of the top-20 songs by `plays_past_50` agreed with and without the duplicates. Umphreys was re-scored afterwards.
- Billy had 16 ghost rows and 2 real duplicate pairs. Its collector had stopped before the oldest shows, so the gap was never filled until #227. Billy was not material to the duplicate issue (0.00 difference), so it was not re-scored.
- After the cleanup, the `plays_past_50` re-measure found 0 duplicates and a top-20 overlap of 1.00 with the reference window. Three duplicates had survived the first cleanup; they are removed now (see the re-measure section).
- Billy 2026-12-09 at Smart Financial Centre had a stray empty duplicate row. It is removed.
- Two stale agent worktrees and their branches were removed.
- The 2026-10-27 correction sweep and the orphan prediction boards were also cleaned up.

## Umphreys: duplicate shows from a URL format change

Around 2026-05-10, `allthings.umphreys.com` added a `/setlists/` path segment to show URLs. `_sync_um_shows_raw` matched stored rows by exact `source_url`. Each re-scraped show therefore got a new row: 23 ghost rows and about 168 duplicate pairs.

Fix: #225 adds `normalize_um_show_url`, which strips the segment. The two `-2` pages (separate shows on the same date) stay distinct.

Cleanup: `dedupe_um_shows.py` dry run found 23 ghosts, 164 pairs, and 2 pairs skipped because `setlist_accuracy` referenced them. The applied run deleted 187 shows (backup `.claude/backups/2026-10-28/dedupe_um_shows_20261028T145307Z.json`). The 2 skipped pairs (show_ids 1773756273 and 1773756291) were deleted with #228's `--delete-referenced-pairs` flag, together with their 2 `setlist_accuracy` rows (backup `.claude/backups/2026-10-28/dedupe_um_shows_20261028T153943Z.json`). Final audit: 0 ghosts, 0 pairs.

Impact: the 169 duplicate shows counted in the step 3.0 check shift the 50-show window start from 2026-03-29 back to 2026-05-01. The count does not match the 189 rows the cleanup targeted (23 + 164 + 2). The difference was not investigated.

## Umphreys: re-score

`backfill-predictions.yml` ran with `band=um`: a dry run (run 40716286201) and then a live run (run 40734393345). The result is one model version, `um_fast_gbm_v12_gap_scaled_p50_venuefix`, with 50 accuracy rows evaluated 2026-10-28 17:18 to 17:21 UTC. None of the rows point at a deleted show.

## Umphreys: `plays_past_50` re-measure

The comparison was re-run on the cleaned data.

- First re-measure, on cleaned data: 3 duplicate shows remained: 2025-04-05 at the Ryman, 2026-04-30 at Moon Palace and 2026-08-21 at Wooly's. Mean absolute p50 difference 0.15. Top-20 overlap mean 0.81, minimum 0.50. Window start 2026-04-30, against 2026-03-29 for the reference.
- Cause: the collector matched existing shows by `source_url` alone. A `/setlists/` URL change on 2026-05-10 and an apostrophe slug change (`wooly039s` to `woolys`, 2026-10-13) each created a second row for the same show. #233 fixes this with a date and venue fallback and apostrophe normalisation. #232 adds the `--delete-ids` mode used for this cleanup.
- Cleanup: deleted show_ids 1743900804, 1773756239 and 1775599432, plus their `setlist_accuracy` rows 2499 and 2471. Kept 1775599289, 1775599384 and 1775599419. Backup: `.claude/backups/2026-10-28/dedupe_um_shows_20261028T175044Z.json`.
- Re-measure after the cleanup: 0 duplicates, mean absolute p50 difference 0.00, top-20 overlap 1.00. Window start 2026-03-29 in both runs.
- The 14 Umphreys VIP-set pages (3 to 4 songs beside a 15 to 20 song main show) are correctly not counted as duplicates. Their song-set Jaccard is 0.0, below the 70% duplicate rule.

The step 3.0 check above is the source of the original 69% figure. The re-measure above is the result for the cleaned data.

## Umphreys: gap checks

Read-only checks found no genuine gaps, so no backfill was dispatched.

- 2026-01-24 First Avenue: canceled by the venue; no upstream setlist; 0 songs is correct.
- 2026-10-04 The Pinnacle: 3 songs, matching upstream (an industry party).
- 2025-10-25 and 2025-11-07: the 3-song and 4-song pages are separate VIP-package setlists. The main shows (20 and 15 songs) match upstream.

Open design question: VIP sets are stored as separate show rows. Whether the model should treat a VIP set as its own show is not decided.

## Billy: duplicate and ghost rows

Cause of the 2026-09-28 duplicate: reconcile required exact normalized venue names. The show was stored under "Pechanga Arena" (show 31152, billybase) and "Pechanga Arena San Diego" (show 29184, bmfsdb).

Fix: #226 reconciles by venue variant and adds `dedupe_billy_shows.py`. #227 reuses a lone same-date row during reconcile.

Re-audit: 36 dates have 2 or more full rows. Only 2 are real duplicates:

- 2019-02-24: show_ids 1201 and 1202 are two bmfsdb records with identical 28-song sets. Kept 1201.
- 2026-09-28: show_ids 31152 and 29184. The apparent 42% overlap was a formatting artifact (trailing ` >` segue markers, curly versus straight apostrophes, title casing). Both have the same 22 songs in the same order. Kept 29184.

The other 34 are genuine: two sets at one festival (for example DelFest, Renewal and Grey Fox), or sit-ins with other artists (Greensky Bluegrass, Dopapod, Willie Nelson). A same-date row is not automatically a duplicate; compare song sets before deleting.

Cleanup: `dedupe_billy_shows.py` deleted 18 shows, namely the 16 ghost rows (show_ids 96, 97, 99, 1194, 1195, 1276, 1364, 1568, 1684, 1686, 3260, 24445, 24447, 27105, 29223, 29233) and show_ids 1202 and 31152. The 31152 delete also removed its `setlist_accuracy` row. Backup: `.claude/backups/2026-10-28/dedupe_billy_shows_20261028T150502Z.json`.

## Billy: gap fill

Cause: `BillyCollector._collect_past_shows` re-parsed the oldest `/past-shows/` card, hit a slug it had already seen, and stopped. Nothing older than 2026-09-25 was ever collected, and no flag combination could work around this. Fixed in #227.

First dispatch (run 40712847969, `--refetch-existing --start-date 2026-04-15`): 19 shows and 291 rows upserted, but none of the 6 target shows changed.

Second dispatch (run 40715101837): 42 shows and 848 rows upserted. Show 29083 (2026-07-31) went from 4 to 26 songs, and show 29098 (2026-08-06) from 5 to 25. No duplicate rows were created.

Phantom rows: Billy Strings was injured in Charlottesville on 2026-04-18 and postponed. The four rows for 2026-04-22 (show_id 25844), 04-24 (26490), 04-25 (26510) and 04-26 (26531) had 0 songs and no accuracy rows. They were deleted (backup `.claude/backups/2026-10-28/delete_billy_postponed_shows_20261028T152448Z.json`). The Charleston and Fishers dates were moved to 2026-08-04 and 2026-08-06, 07 and 08, and those dates already had rows.

Note: bmfsdb rows are never refetched, because bmfsdb was dropped from billy collection in #195, and the setlist parser cannot read bmfsdb pages.

## Billy: 2026-12-09 Smart Financial Centre

Two empty future rows existed for the same show: show_id 30796 (bmfsdb uuid, venue "Smart Financial Centre at Sugar Land") and show_id 31138 (billybase URL, venue "Smart Financial Centre"). Neither had setlist, accuracy or prediction rows.

Kept 31138 and deleted 30796 with #230's allowlist, run with `--delete-show-id 30796`. Backup: `.claude/backups/2026-10-28/dedupe_billy_shows_20261028T174514Z.json`. A dry run afterwards found 0 ghosts and 0 pairs.

Reconcile (#226 and #227) picks the exact venue match, so the next scrape should not add a third row. This is not confirmed yet: it has not been observed on a live scrape.

## Correction sweep and orphan boards

The correction sweep (#215 to #219, with the `replace_show_setlist` migration applied to hosted Supabase) corrected 35 setlists: wsp 16, um 8, billy 6, goose 1, phish 4.

#224 removed superseded model-version boards. The prune deleted 7 `setlist_predictions` rows and 300 `setlist_prediction_songs` rows across 5 bands, leaving one model version per band. Backups: `.claude/backups/2026-10-28/prune_old_model_versions_<band>_20261028T1430*.json`, one per band. Hosted smoke run 40706648980 was green.

## Other fixes merged in this session

- #221: stale docs and unused web exports removed.
- #222: WSP skips future shows.
- #223: accuracy freshness is correct when every show is already scored.
- #231: song board search pill left-aligned.

## Worktrees and branches

Stale agent worktrees `agent-aab6f4b6fe6596337` and `agent-aad104f3b92f1db34` were removed. Their PRs #218 and #219 were already merged. The local and remote branches `connorkitchings/fix-sweep-payload-timestamps` and `connorkitchings/fix-sweep-encore-positions` were deleted too.

## Open items

Not fixed, and not in scope for this session:

- 145 Billy rows with 0 songs and no full sibling. Most are past shows with no upstream setlist.
- The correction sweep's `match_upstream_shows` uses exact `date_venue` keys, so a show stored under a venue variant goes unmatched. It cannot create duplicates, and it was not changed.
- In reconcile, when two existing same-date rows both match and both have setlists, the outcome is not fully determined.
- VIP sets as separate show rows (see above).
- The step 3.0 duplicate count (169) does not match the cleanup targets (189). Not investigated.

## Daily run check

Not confirmed as of this write-up. Each of these stays open until the next scheduled run shows it:

- The next scheduled WSP daily run has no `DOM fingerprint mismatch` for 2027 shows.
- Goose `freshness_state` is not stale.
- `Daily Data Pipeline` is green for all bands.

Result of the daily run check:

DAILY_RUN_RESULT_PLACEHOLDER
