# Session Log: Harden Admin Setlist Tool for Manual WSP Entry

Date: 2026-06-25
Branches: `feat/admin-setlist-hardening` (#174, merged)
Context: WSP plays Red Rocks 2026-06-26. Everyday Companion lags completed shows, so the 6/27 19:00 UTC prediction pipeline would hard-fail (`failed_upstream_stale`) or train on stale history without the 6/26 setlist.

## Goal

Enable reliable manual setlist entry into the site so the 6/27 prediction workflow runs correctly when EC is slow.

## Constraints

- Never work on `main`; feature branch only (AGENTS.md rule 6).
- Preserve the existing auth gate (`src/proxy.ts` + HMAC cookie) — no second auth mechanism.
- Route handlers only (repo has zero `"use server"`); service-role client only inside route handlers.
- Keep `verify:web` green (unit + lint + build + smoke) and `verify:clean` clean.
- Every logic change needs tests (rule 7); docs updated when entrypoints change (rule 8).
- Time-boxed: small focused PR before the 6/26 show.

## Key Finding

A manual setlist entry tool **already existed** and was deployed at `/admin/setlist` (merged in `6e21b87d`, hardened in `0f36a50e`). The task was to harden it, not build it. Four gaps threatened the 6/26 scenario:

1. **Duplicate-show risk (critical).** `ensureShow` matched existing shows by exact `(show_date, venue_name)`. Preflight confirmed 6/26 already exists as `show_id=22466` with `venue_name="Red Rocks"` (not "Amphitheatre"). A slight venue-string mismatch would create a duplicate show row and orphan the setlist in the prediction's date-dedup.
2. **Comma-titled songs split.** The web parser split naïvely on commas; WSP titles like "Lawyers, Guns, And Money" fragmented into multiple rows and broke gap features (case-sensitive grouping).
3. **No read-back verification** after submit.
4. **No edit/delete** recovery path.

## Preflight (read-only Supabase)

- 6/26 show exists: `show_id=22466`, venue `"Red Rocks"`, city `Morrison`, state `CO`, `source_url=https://www.everydaycompanion.com/setlists/20260626a.asp`.
- 6/26 has 0 setlist rows (clean slate).
- `source` column exists on `wsp_setlists_raw` (values: `everydaycompanion`, `panicstream`). Out of scope for this PR; `source=NULL` rows are safe from EC-over-fallback cleanup.
- 6/27 target show exists (`show_id=22467`) → `_resolve_next_show` will resolve correctly.

## Commands Run

```bash
# Preflight (read-only)
uv run python /tmp/preflight_wsp.py   # one-off; confirmed 6/26 show + source column

# Local verification gates
npm run test:unit                     # 38 unit tests (8 new) green
npm run lint                          # eslint clean
npm run build                         # next build + TS green
npm run test:web:smoke                # 8 passed, 8 skipped (project guards)
npm run verify:web                    # canonical gate green
npm run verify:docs                   # mkdocs --strict green
npm run verify:clean                  # clean baseline post-commit

# CI + merge
gh pr create --base main ...          # PR #174
gh pr checks 174                      # all green (Verify Repository, Verify Website, Vercel, GitGuardian)
gh pr merge 174 --squash --delete-branch
```

## Files And Artifacts

- `apps/web/src/lib/admin/setlist-parser.ts` (new) — pure parser shared by route + client preview; ports WSP comma-song protection + case canonicalization from `src/jambandnerd/data_collection/wsp/parser.py:35`.
- `apps/web/src/app/api/admin/setlist/route.ts` — added `GET /api/admin/shows` (read-only show list + row counts), `DELETE /api/admin/setlist` (clear one show's rows), optional `showId` on `POST`, returns parsed rows for read-back.
- `apps/web/src/components/admin-setlist-form.tsx` — show picker with existing-row badges, inline saved-rows read-back grouped by set, on-site link, clear-and-re-enter action.
- `apps/web/tests/unit/setlist-parser.test.ts` (new) — 8 unit tests.
- `docs/operations/website_delivery.md` — documented the new admin endpoints + `SUPABASE_SERVICE_ROLE_KEY` requirement.
- Version bump 1.0.1 → 1.0.2 (patch: internal tooling) across `pyproject.toml`, `src/jambandnerd/__init__.py`, `apps/web/package.json`, `apps/web/src/lib/site.ts`, `uv.lock`.

## Validation

| Check | Status |
|---|---|
| `npm run test:unit` (38, incl. 8 new) | PASS |
| `npm run lint` | PASS |
| `npm run build` (TS strict) | PASS |
| `npm run test:web:smoke` (8) | PASS |
| `npm run verify:docs` (mkdocs --strict) | PASS |
| `npm run verify:clean` | PASS |
| CI Verify Repository | PASS |
| CI Verify Website | PASS |
| Vercel Production deploy (commit `2587ad46`) | success |

## Data-Path Verification (why this is safe for 6/27)

- `POST` with `showId` attaches the setlist to the existing `show_id=22466` → no duplicate show, no date-dedup orphaning.
- `skip_existing_setlists=True` (WSP collection policy) means collection on 6/27 will not disturb manually-entered rows.
- `source=NULL` rows are not in the EC-over-fallback delete set (`panicstream`/`tourwrangler` only).
- `generate_live_predictions.py` reads `wsp_shows_raw` + `wsp_setlists_raw` fresh at 6/27 19:00 UTC; 6/26 (`show_date < reference_date`) becomes history; 6/27 (`show_id=22467`) is the target. No flag or skip needed.

## Remaining Steps (user action)

1. **Enter the 6/26 setlist** via `jambandnerd.com/admin/setlist` once it's live (Production deploy `2587ad46` = success). Log in → `wsp` + `2026-06-26` → reuse show 22466 → paste setlist → review preview/read-back → submit.
2. **Verify**: open `/last-show?band=wsp` (or re-run the read-only preflight query for 6/26 setlist rows).
3. Confirm the 6/27 19:00 UTC daily pipeline stays green and the WSP prediction regenerates with 6/26 in history.

## Next Step

- (Owner: user) Enter 6/26 setlist after the show; verify per above.
- (Follow-up, out of scope this PR) Tag web-entered rows with `source='manual'` via schema-sniff; generalize the `if (band === "wsp") source_hash` carve-out into band-schema metadata.

## Durable Lesson

Before building a net-new internal tool, audit `/admin` and `src/app/api/admin` for an existing scaffold — this repo already had a deployed, auth-gated, service-role write path that was the correct extension target. Greenfield would have duplicated the auth + parser + Supabase infrastructure and delayed the fix past the show deadline.
