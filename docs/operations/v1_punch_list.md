# v1.0 Pre-Launch Punch List

Comprehensive review of every page and component in `apps/web/`. File references are relative to `apps/web/src/`. 30 items.

## Critical / Accessibility

1. **Missing `focus-visible` on navigation links** — Interactive elements in 7 files lack visible focus rings. Screen-reader and keyboard-only users cannot see which element is focused.
   - `components/site-header.tsx:49` — mobile back button has no `focus-visible:ring`
   - `components/site-header.tsx:100` — desktop nav links have no `focus-visible:ring`
   - `components/mobile-bottom-nav.tsx:24` — all 4 bottom nav links
   - `components/k-toggle.tsx:39` — toggle buttons
   - `components/contact-actions.tsx:34` — copy email button
   - `components/filter-links.tsx:56` — band pills
   - `components/dashboard-side-nav.tsx:66` — band grid links
   - Fix: add `focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none` to each.

2. **`components/expandable-panel.tsx:29-48`** — expand/collapse buttons missing `aria-expanded` and `aria-controls`. Screen readers cannot determine toggle state or which content region is controlled.

3. **`components/song-search.tsx:96-132`** — no "no results found" state. When a user searches and nothing matches, the input stays open with no feedback. Add a result row or message: "No songs found matching '...'".

4. **`components/mobile-control-selects.tsx:32-43`** — each `<select>` has both a wrapping `<label>` (line 32) and an `aria-label` (line 38). The `<label>` is not linked to the `<select>` via `htmlFor`/`id`. Pick one pattern (prefer explicit `id` + `htmlFor`).

5. **Homepage mobile CTAs missing** — `app/page.tsx:99` — "View Predictions" and "See Performance" buttons are `hidden md:grid`. Mobile users landing on `/` see no primary call-to-action buttons. Add mobile equivalents or unhide the existing buttons (they're already full-width styled).

6. **Heading hierarchy audit** — `components/prediction-hero.tsx` and `components/page-hero.tsx` both render `<h1>`. `components/data-state.tsx` renders `<h2>`. Currently each page renders only one of these heroes, so no duplicates exist — but this is fragile and undocumented. Add a lint comment or runtime invariant check.

## UX / Functional

7. **Song name truncation missing on mobile** — `components/song-board.tsx:237` — mobile list song names have no `truncate` class. Long names (e.g., "Miss the Mississippi and You") will overflow the card.

8. **`normalizeSongName` duplicated** — `app/replay/page.tsx:55` and `app/last-show/page.tsx:41` both define the same function. Move to `lib/song-board-core.ts` or `lib/format.ts`.

9. **Top-K hit computation duplicated** — `app/replay/page.tsx:59-75` defines `computeTopKHits` and `computeTopKRecall`. `app/last-show/page.tsx:102-109` recomputes hits manually with `.slice(0, 10).filter()`. Use a shared helper from `lib/` for both.

10. **`app/last-show/page.tsx`** — only shows Top-10 hits comparison in the aside panel. Replay page shows both Top-10 and Top-25. Add Top-25 and Top-50 hits counts for consistency.

11. **`app/predictions/page.tsx:241`** — description text says "clustering tonight" even when `displayState` is "previous" or "next". Conditionally change the copy based on `displayState`.

12. **Double `editorial-panel` nesting on predictions** — `app/predictions/page.tsx:230` wraps the `<SongBoard>` in its own `editorial-panel`, and `<SongBoard>`'s `<TierSection>` (line 282) also renders `editorial-panel`. Creates double-border visual nesting. Remove the outer panel or the inner panels.

13. **`components/prediction-hero.tsx:97`** — `headlineLocation = locationLabel || venueName`. When a location label exists (e.g., "Chicago, IL"), it becomes the `<h1>` instead of the venue name. The venue name is more specific and interesting to users. Swap priority: venue name should be the headline, location should be subordinate.

14. **`components/recall-chart.tsx`** — SVG chart uses fixed viewBox with `preserveAspectRatio="xMidYMid meet"`. On very wide screens (>1200px) the chart expands to fill width, making dot markers and labels disproportionately small. Cap the container at a max render width (~900px).

15. **`components/setlist-columns.tsx:150-152`** — mobile setlist uses comma-separated inline flow; encore set renders as a separate full-width card on desktop. Fine for current use but the split between `MobileSetlistFlow` and `SetGroupCard` could be unified into a single render path.

## Content & Copy

16. **`app/data-use/page.tsx:67`** — uses `...` (three ASCII dots) instead of `…` (ellipsis character). Replace with `…` or `&hellip;`.

17. **`components/prediction-hero.tsx:150`** — "How To Read It" section text. Uses straight quotes if present. Audit all user-facing copy for curly quotes `"` `"`.

18. **`app/contact/page.tsx:53`** — "By submitting data corrections, you grant..." paragraph appears at the bottom of a contact page with no submission form. Either remove the license grant text or move it to a page where data submission actually occurs (e.g., Admin setlist page).

19. **`app/performance/page.tsx:114`** — uses the term "slippage" which is financial jargon. Consider "drift", "variation", or "consistency" instead.

## Code Quality / Architecture

20. **Repeated error/empty state boilerplate** — Every page duplicates the same 4-state check pattern (`missing_env`, `error`, `empty`, `ready`). Extract a shared `DataGate` component that accepts a `RouteState` and renders the appropriate fallback or delegates to children.

21. **`app/predictions/page.tsx:195-203`** — `process.env.SUPABASE_URL` and `SUPABASE_ANON_KEY` are passed as props to `<LiveTracker>`, which serializes them into client-side HTML. Use `NEXT_PUBLIC_` prefix for intentional public exposure, or refactor to avoid serializing server env vars into client bundles.

22. **`components/live-tracker.tsx:36`** — creates a new `createClient()` on every component mount. While the dependency array makes this stable per band/show, a module-level singleton Supabase client would be cleaner and avoid re-initializing the WebSocket connection on route changes.

23. **`app/page.tsx:15-20`** — `HOME_TEASER_BANDS` is hardcoded to 4 bands. The Supabase `bands` table is the canonical source of truth. If a band is renamed or removed in Supabase, the teaser silently shows stale data. Derive teaser bands from the fetched `bands` result, using the hardcoded list only as fallback.

24. **`app/performance/page.tsx:92-97`** — computes `top10Average`, `top25Average`, `top50Average`, `p10Average`, `p25Average`, `p50Average` by calling `state.rows.map(...)` six separate times, iterating the same array six times. Combine into one precomputed set of mapped arrays.

## Minor / Polish

25. **`components/song-search.tsx:73`** — search `<input>` missing `autocomplete="off"` and `spellCheck={false}`. Song names are not dictionary words and password managers may trigger on the search field.

26. **`app/about/page.tsx:123`** — FAQ `<details>` elements all start closed. Consider opening the first FAQ item by default (`defaultOpen` or `open` attribute) for better initial UX.

27. **`components/setlist-columns.tsx:41-55`** — `getGridClassName` handles 1–4 sets but has no explicit 5+ set case. Most bands play 2–3 sets; 4+ is rare but the fallback grid should always be well-defined.

28. **`app/globals.css:51-55` and `:57-63`** — both `<html>` and `<body>` declare radial gradient backgrounds. The `<body>` gradient visually overrides `<html>`'s. Remove the dead `<html>` background or consolidate.

29. **`components/prediction-hero.tsx`** — component is semantically overloaded: it renders the show hero (date, venue, status badge) AND the model performance metric panel (3 cards). Consider splitting into `ShowHero` (context) and inline `<MetricPanel>` in the page. Reduces prop count and single-responsibility concerns.

30. **`components/dashboard-side-nav.tsx` and `components/filter-links.tsx`** — both render band pills with nearly identical active/hover styling but different public APIs (`FilterLinks` takes `date`, `DashboardSideNav` doesn't). Extract a shared `BandPillGrid` component.

---

## Summary

| Priority | Count | Focus |
|----------|-------|-------|
| Critical (a11y) | 6 | focus-visible rings, aria-expanded, label linkage, heading audit |
| UX / Functional | 9 | truncation, code dedup, empty states, navigation consistency |
| Content / Copy | 4 | ellipsis, curly quotes, terminology, misplaced copy |
| Code Quality | 5 | shared state gate, env exposure, client singleton, perf |
| Minor / Polish | 6 | autocomplete, dead CSS, FAQ default-open, component reuse |

No data-corruption or crash bugs found. Core prediction/performance/replay data flows are sound. Primary risk areas are keyboard/screen-reader accessibility and mobile UX gaps on the homepage.
