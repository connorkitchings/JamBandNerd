# Billy Upcoming-Shows Scraper — Livewire Hydration Fix

## Goal

- The follow-up to `01_billy_no_upcoming_show_fix.md`. After shipping the no-upcoming-show prediction gate, the user flagged that Billy Strings DOES have upcoming shows but our data had none. Investigate and fix.

## Constraints

- No DB schema or model behavior changes.
- Stay on bmfsdb as the sole Billy source (no alternate feed).
- Keep `npm run verify:python` and `npm run verify:docs` green.
- Do not work on `main`; feature branch off main.

## Diagnosis

`billy_shows_raw` had **0 future rows** (queried live; last captured show `2026-07-28 | Hartford`). The user is correct that Billy has announced dates, but two distinct problems were conflated:

1. **bmfsdb currently lists zero upcoming Billy shows.** Confirmed by rendering `https://bmfsdb.com/setlists?view=upcoming` with a real Playwright Firefox browser: the past view hydrates 10 `/setlist/` anchors cleanly, but the upcoming view renders zero show entries. bmfsdb is community-maintained; Billy's fall dates are not entered there yet. This is upstream, not our bug.

2. **Our scraper IS broken (latent).** bmfsdb migrated the upcoming view to **Livewire 3**. `_collect_upcoming_shows` did a plain `requests.get` + `soup.select("a.link-unstyled")`, but `link-unstyled` appears **0 times** in the server HTML (the show list loads via a JS-driven Livewire POST). Decisive probe: `requests` on `?page=1` (past) returns `link-unstyled=10` (server-rendered, works); `?view=upcoming` returns `link-unstyled=0` (Livewire-only, broken). So the past-shows scrape works but the upcoming scrape silently returned `[]` — meaning the moment bmfsdb lists shows again, we still would not capture them.

## Fix

Route only the upcoming-shows fetch through Playwright. The past-shows path is untouched (it is still server-rendered).

- `src/jambandnerd/data_collection/browser.py` — new `CloudflareBypass.render_html(url, *, wait_for_selector, wait_until, selector_timeout_ms, ...)` method. Like `make_request` but waits for a CSS selector so Livewire/JS content is present. If the selector never appears (source legitimately empty), the current DOM is returned without raising.
- `src/jambandnerd/data_collection/billy/collector.py` — split `_collect_upcoming_shows` into `_fetch_upcoming_soup` (try `requests`; if 0 cards, fall back to `CloudflareBypass.render_html` with `wait_for_selector="a.link-unstyled"`, `wait_until="networkidle"`) and `_parse_upcoming_cards` (the existing card parser, unchanged). Lazy `from ..browser import CloudflareBypass` so non-upcoming paths pay no import cost.
- `scripts/run_billy_collection.py` — import `CloudflareBypass` and call `cleanup()` at the end of collection (mirrors Eggy).
- `.github/workflows/daily-pipeline.yml` — add `|| matrix.band == 'billy'` to the three Playwright OS-deps / cache / install-browsers steps.
- `docs/operations/github_actions.md` — new "Billy Upcoming-Shows Hydration" subsection; note Playwright is now installed for WSP + Eggy + Billy.

## Commands Run

```bash
# Live DB check (0 future Billy rows confirmed)
. ./.env && uv run python -c "from scripts.common import fetch_table_rows; ..."

# Confirmed requests sees 0 cards on upcoming but 10 on past page=1
uv run python -c "from bs4 import BeautifulSoup; ..."

# Playwright probes (Firefox): past view = 10 anchors; upcoming = 0 (source empty)
uv run python -m playwright install firefox

# Verify on the branch
npm run verify:python   # 619 passed, 10 deselected
npm run verify:docs     # exit 0

# End-to-end check of the new fallback path against live bmfsdb
uv run python -c "from src.jambandnerd.data_collection.billy.collector import BillyCollector; ..."   # 0 shows, no crash
```

## Files And Artifacts

- Branch `fix/billy-upcoming-livewire-scraper` (off `main` @ `b2ba8f4e`).
- `tests/data_collection/test_billy_collector.py` — 3 new tests:
  - `test_parse_upcoming_cards_extracts_show` (parser unit test, min_date filter).
  - `test_collect_upcoming_shows_falls_back_to_browser_when_ssr_empty` (asserts `render_html` is invoked with `wait_for_selector="a.link-unstyled"` / `wait_until="networkidle"` when SSR has 0 cards).
  - `test_collect_upcoming_shows_uses_ssr_when_cards_present` (asserts no browser fallback when SSR returns cards).

## Validation

- `verify:python`: 619 passed (616 baseline + 3 new), 10 deselected.
- `verify:docs`: exit 0.
- Live end-to-end: `_collect_upcoming_shows(date.today())` returns 0 via the Playwright fallback without crashing (bmfsdb currently lists no upcoming Billy shows). When bmfsdb lists shows again, the identical `a.link-unstyled` card structure (proven by the past-view hydration) will be captured.
- A pre-existing test (`test_collect_songs_uses_canonical_trailing_slash_url`) was momentarily broken by an indentation slip in the initial append edit (`collect_songs()` shifted outside its `with patch.object` block); restored, and the full Billy suite passes in 0.22s (no real network).

## Next Step

- Open PR `fix/billy-upcoming-livewire-scraper` -> `main`, watch CI, merge.
- This does not manufacture upcoming-show data. Once bmfsdb's community enters Billy's next tour, the daily pipeline will capture it automatically via the new Playwright path. Monitor the first Billy run after bmfsdb lists shows to confirm ingestion.
- Optional follow-up (declined this session): add an alternate Billy upcoming-shows source to avoid bmfsdb community-entry lag.
