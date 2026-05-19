# v1.0 Pre-Launch Punch List

Comprehensive review of every page and component in `apps/web/`. File references are relative to `apps/web/src/`. Items are organized by priority, then by effort within each tier. Each item carries a risk tag.

## Risk Tags

| Tag | Meaning |
|-----|---------|
| **SHIELD** | Security or compliance exposure — fix before launch |
| **BLOCK** | Blocks a user segment (keyboard, screen-reader, mobile) |
| **LEAK** | Wasted compute, bundle bloat, or dead code |
| **DRIFT** | Content, copy, or UX inconsistency — degrades trust |
| **FRICTION** | Developer experience or maintainability concern |

## Implementation Status: 2026-05-18

All launch punch-list items have been addressed for local V1 readiness after a second implementation audit.

- Items #2–37 were implemented in the web app, docs, or tests.
- Item #1 was intentionally kept as `src/proxy.ts`: Next.js 16.2 recognizes and prefers `proxy.ts`; renaming to `middleware.ts` introduces a framework deprecation warning.
- Medium refactor items are complete: route states now use `DataGate`, prediction metrics are split out of the show hero, setlist columns share one render path, and band pill links share `BandPillGrid`.
- Heading hierarchy is guarded by the public-shell smoke test, which now asserts exactly one `<h1>` on public routes.
- Local checks completed during implementation: `npm run test:web:unit`, `npm run lint:web`, `npm run build:web`, `npm run test:web:smoke:list`, `npm run test:web:smoke`, `npm run verify:web`, `npm run verify:docs`, and `npm run verify:clean`.
- Final deployment remains prepare-only: no push, PR, merge, hosted smoke, or production deploy was performed from this pass.

## Independent Follow-Up: 2026-05-17

Fresh route-level review covered `/`, `/predictions`, `/performance`, `/replay`, `/last-show`, `/about`, `/contact`, `/data-use`, `/admin/setlist`, `/preview/tables`, and removed routes `/compare` and `/explorer` at desktop and mobile sizes. The review intentionally happened before reading this punch list.

Resolved during the follow-up:
- `app/admin/setlist/page.tsx` now renders an `Admin Access` `<h1>` and status text while the session check is pending.
- `app/replay/page.tsx` now stacks the prediction board and actual setlist sections, fixing the cramped desktop replay table where song names could disappear and removing the stretched empty actual-setlist panel.

Deferred finding:
- **Performance ledger duplicate-looking rows** — `/performance` currently displays repeated same-date/same-venue rows in the recent accuracy ledger. This may represent multiple retained model snapshots or duplicate source rows, so fix only after confirming the intended `setlist_accuracy` read contract. Candidate fixes: filter to the active model version, dedupe by canonical show key, or expose model/version context in the table so repeated rows are explainable.

---

## Critical / Security / Accessibility

### 1. `proxy.ts` naming — non-standard middleware filename [FRICTION]
- **File:** `src/proxy.ts`
- **Effort:** Trivial — rename to `src/middleware.ts` for convention, or leave as-is
- **Risk:** Low. Confirmed: Next.js 16 recognizes `proxy.ts` as middleware (build output shows `ƒ Proxy (Middleware)`). Admin routes **are protected** in production. Rename only for developer clarity — `middleware.ts` is the expected convention and reduces onboarding confusion.
- **Status:** Downgraded from SHIELD to FRICTION after build verification on 2026-05-17.

### 2. Missing `focus-visible` on navigation links [BLOCK]
- **Files:** `components/site-header.tsx:49,100`, `components/mobile-bottom-nav.tsx:24`, `components/k-toggle.tsx:39`, `components/contact-actions.tsx:34`, `components/filter-links.tsx:56`, `components/dashboard-side-nav.tsx:66`
- **Effort:** Low — add `focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none` to each interactive element
- **Risk:** Keyboard-only and screen-reader users cannot see which element is focused.

### 3. `expandable-panel.tsx` missing `aria-expanded` and `aria-controls` [BLOCK]
- **File:** `components/expandable-panel.tsx:29-48`
- **Effort:** Low — add `aria-expanded={isExpanded}` and `aria-controls` pointing to the body region
- **Risk:** Screen readers cannot determine toggle state or which content region is controlled.

### 4. `mobile-control-selects.tsx` label not linked to `<select>` [BLOCK]
- **File:** `components/mobile-control-selects.tsx:32-43`
- **Effort:** Low — add `id` to `<select>` and `htmlFor` on `<label>`, or remove the redundant `aria-label`
- **Risk:** The wrapping `<label>` is not programmatically associated with the control.

### 5. Homepage mobile CTAs hidden [BLOCK]
- **File:** `app/page.tsx:99`
- **Effort:** Low — remove `hidden md:grid` or add mobile-equivalent buttons
- **Risk:** Mobile users landing on `/` see no primary call-to-action buttons.

### 6. `song-search.tsx` no "no results" state [DRIFT]
- **File:** `components/song-search.tsx:96-132`
- **Effort:** Low — add a result row or message when `results.length === 0 && query.trim().length > 0`
- **Risk:** User searches, gets zero matches, and receives no feedback.

### 7. Heading hierarchy undocumented [FRICTION]
- **Files:** `components/prediction-hero.tsx`, `components/page-hero.tsx` (both `<h1>`), `components/data-state.tsx` (`<h2>`)
- **Effort:** Low — add a lint comment or runtime invariant check that each page renders exactly one `<h1>`
- **Risk:** Fragile — adding a second hero to a page would create duplicate `<h1>` elements.

---

## UX / Functional

### 8. No `loading.tsx` — blank screens during server fetches [DRIFT]
- **Scope:** All 10 page routes; at minimum `/predictions`, `/performance`, `/replay`, `/last-show`
- **Effort:** Medium — add `loading.tsx` files with skeleton UI matching each route's layout
- **Risk:** With server-side Supabase reads, users see a blank screen until the full page renders. No streaming suspense boundaries exist anywhere.

### 9. No `error.tsx` or `not-found.tsx` — unhandled errors break design [DRIFT]
- **Scope:** All page routes
- **Effort:** Medium — add route-level `error.tsx` with recovery button and site-wide `not-found.tsx`
- **Risk:** Any unhandled server error or 404 falls through to default Next.js pages, breaking the site's visual design and providing no recovery path.

### 10. Song name truncation missing on mobile [DRIFT]
- **File:** `components/song-board.tsx:237`
- **Effort:** Low — add `truncate` class to mobile list song names
- **Risk:** Long names (e.g., "Miss the Mississippi and You") will overflow the card.

### 11. `normalizeSongName` duplicated across two pages [FRICTION]
- **Files:** `app/replay/page.tsx:55`, `app/last-show/page.tsx:41`
- **Effort:** Low — move to `lib/format.ts` or `lib/song-board-core.ts`
- **Risk:** Drift if one copy is changed and the other is not.

### 12. Top-K hit computation duplicated across two pages [FRICTION]
- **Files:** `app/replay/page.tsx:59-75` defines `computeTopKHits`/`computeTopKRecall`; `app/last-show/page.tsx:102-109` recomputes hits manually with `.slice(0, 10).filter()`
- **Effort:** Low — extract shared helpers to `lib/format.ts` or `lib/song-board-core.ts`
- **Risk:** Same as #11 — logic drift between copies.

### 13. `last-show` only shows Top-10 hits [DRIFT]
- **File:** `app/last-show/page.tsx`
- **Effort:** Low — add Top-25 and Top-50 hit counts to match replay page
- **Risk:** Inconsistent metric exposure between similar routes.

### 14. Predictions description says "clustering tonight" for all states [DRIFT]
- **File:** `app/predictions/page.tsx:241`
- **Effort:** Low — conditionally change copy based on `displayState`
- **Risk:** Misleading text when showing previous or next shows.

### 15. Double `editorial-panel` nesting on predictions [DRIFT]
- **File:** `app/predictions/page.tsx:230` wraps `<SongBoard>`, which also renders `editorial-panel` in its `<TierSection>` (line 282)
- **Effort:** Low — remove the outer panel or the inner panels
- **Risk:** Double-border visual nesting degrades the design.

### 16. `prediction-hero.tsx` headline priority inverted [DRIFT]
- **File:** `components/prediction-hero.tsx:97` — `headlineLocation = locationLabel || venueName`
- **Effort:** Low — swap: venue name as headline, location as subordinate
- **Risk:** Generic "Chicago, IL" shown instead of the more specific venue name.

### 17. `recall-chart.tsx` scales poorly on wide screens [DRIFT]
- **File:** `components/recall-chart.tsx`
- **Effort:** Low — cap container at `max-w-[900px] mx-auto`
- **Risk:** On screens >1200px the chart expands, making dot markers and labels disproportionately small.

### 18. `setlist-columns.tsx` split render paths [FRICTION]
- **File:** `components/setlist-columns.tsx:150-152`
- **Effort:** Medium — unify `MobileSetlistFlow` and `SetGroupCard` into a single render path
- **Risk:** Maintenance burden; changes must be applied twice.

---

## Code Quality / Performance

### 19. Repeated error/empty state boilerplate across all pages [FRICTION]
- **Scope:** Every page duplicates the 4-state check (`missing_env`, `error`, `empty`, `ready`)
- **Effort:** Medium — extract a shared `DataGate` component
- **Risk:** High cognitive load for new contributors; drift if one page adds a new state.

### 20. Env vars serialized into client bundle [SHIELD]
- **File:** `app/predictions/page.tsx:195-203` — `process.env.SUPABASE_URL` and `SUPABASE_ANON_KEY` passed as props to `<LiveTracker>`
- **Effort:** Low — rename to `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` for intentional public exposure, or refactor to avoid serializing
- **Risk:** Server env vars leak into client-side HTML without explicit `NEXT_PUBLIC_` prefix.

### 21. Supabase client re-created on every mount [LEAK]
- **File:** `components/live-tracker.tsx:36` — `createClient()` per mount
- **Effort:** Low — use a module-level singleton
- **Risk:** Re-initializes WebSocket connection on route changes.

### 22. Hardcoded teaser bands vs Supabase source of truth [DRIFT]
- **File:** `app/page.tsx:15-20` — `HOME_TEASER_BANDS`
- **Effort:** Low — derive teaser bands from fetched `bands` result, hardcoded list as fallback only
- **Risk:** If a band is renamed or removed in Supabase, the teaser silently shows stale data.

### 23. Performance page iterates `state.rows` six times [LEAK]
- **File:** `app/performance/page.tsx:92-97`
- **Effort:** Low — precompute mapped arrays in one pass
- **Risk:** Wasted compute on every server render.

### 24. `recall-chart.tsx` computes `linePath` twice [LEAK]
- **File:** `components/recall-chart.tsx:38-44` — `buildPath().areaPath()` recomputes the line string internally
- **Effort:** Low — have `areaPath` reuse the result of `linePath`
- **Risk:** Wasted computation on every chart render.

### 25. `recall-chart.tsx` maps `chronological` three times [LEAK]
- **File:** `components/recall-chart.tsx:56-58` — one `.map()` per series
- **Effort:** Low — single pass that builds all three series simultaneously
- **Risk:** Unnecessary iteration over the same array.

### 26. `lib/data.ts` vs `lib/data/` naming collision [FRICTION]
- **Files:** `lib/data.ts` (aggregate re-export) alongside `lib/data/` directory
- **Effort:** Low — rename aggregate to `lib/data/index.ts` or `lib/data-facade.ts`
- **Risk:** Import confusion for contributors (`@/lib/data` vs `@/lib/data/bands`).

---

## Content & Copy

### 27. ASCII dots instead of ellipsis [DRIFT]
- **File:** `app/data-use/page.tsx:67`
- **Effort:** Trivial — replace `...` with `…`
- **Risk:** Typographic inconsistency.

### 28. Straight quotes in user-facing copy [DRIFT]
- **File:** `components/prediction-hero.tsx:150` and all user-facing text
- **Effort:** Trivial — audit and replace with curly quotes `" "` where appropriate
- **Risk:** Typographic polish.

### 29. Misplaced license grant on contact page [DRIFT]
- **File:** `app/contact/page.tsx:53`
- **Effort:** Low — remove or move to admin setlist page where data submission occurs
- **Risk:** Confusing — no submission form exists on the contact page.

### 30. "Slippage" is financial jargon [DRIFT]
- **File:** `app/performance/page.tsx:114`
- **Effort:** Trivial — replace with "drift", "variation", or "consistency"
- **Risk:** Terminology mismatch for non-financial audience.

---

## Minor / Polish

### 31. Search input missing `autocomplete` and `spellCheck` [DRIFT]
- **File:** `components/song-search.tsx:73`
- **Effort:** Trivial — add `autocomplete="off"` and `spellCheck={false}`
- **Risk:** Password managers may trigger; spell-check underlines song names.

### 32. FAQ items all start closed [DRIFT]
- **File:** `app/about/page.tsx:123`
- **Effort:** Trivial — add `open` attribute to first `<details>` element
- **Risk:** Users land on FAQ with no content visible.

### 33. `getGridClassName` has no explicit 5+ set case [DRIFT]
- **File:** `components/setlist-columns.tsx:41-55`
- **Effort:** Trivial — add explicit `default` case with sensible grid
- **Risk:** Rare but undefined behavior for 5+ set shows.

### 34. Dead `<html>` background gradient [LEAK]
- **File:** `app/globals.css:51-55` (html) and `:57-63` (body)
- **Effort:** Trivial — remove the `<html>` gradient; `<body>` overrides it
- **Risk:** Dead CSS bytes.

### 35. `prediction-hero.tsx` semantically overloaded [FRICTION]
- **File:** `components/prediction-hero.tsx` — renders show hero AND model performance metrics
- **Effort:** Medium — split into `ShowHero` and inline `<MetricPanel>`
- **Risk:** High prop count, single-responsibility violation.

### 36. Band pill grid duplication [FRICTION]
- **Files:** `components/dashboard-side-nav.tsx` and `components/filter-links.tsx`
- **Effort:** Medium — extract shared `BandPillGrid` component
- **Risk:** Nearly identical active/hover styling maintained in two places.

### 37. Empty directories `_preview/tables/` and `preview/tables/` [LEAK]
- **Scope:** `app/_preview/tables/` and `app/preview/tables/`
- **Effort:** Trivial — delete both directories
- **Risk:** Dead code; confusion about which path is active.

---

## Summary

| Priority | Count | Effort Profile | Key Risks |
|----------|-------|----------------|-----------|
| Critical (a11y) | 6 | 6 Low | BLOCK: keyboard/screen-reader/mobile users |
| UX / Functional | 11 | 8 Low, 3 Medium | DRIFT: inconsistent UX across routes; no loading/error states |
| Code Quality / Performance | 8 | 6 Low, 2 Medium | SHIELD: env leak; LEAK: wasted compute; FRICTION: maintainability |
| Content / Copy | 4 | 3 Trivial, 1 Low | DRIFT: typography, terminology, misplaced copy |
| Minor / Polish | 8 | 4 Trivial, 4 Medium | LEAK: dead CSS/dirs; FRICTION: component reuse, proxy naming |

**Total: 37 items** (30 original + 1 deferred + 6 new; #1 downgraded after build verification)

### Effort Distribution

| Effort | Count |
|--------|-------|
| Trivial | 7 |
| Low | 20 |
| Medium | 10 |

### Recommended Fix Order

1. **#2–7 Critical a11y** (BLOCK, all Low) — unblock user segments
2. **#20 env vars** (SHIELD, Low) — prevent server env leak
3. **#8–9 loading/error boundaries** (DRIFT, Medium) — baseline UX resilience
4. **#11–12 code dedup** (FRICTION, Low) — quick wins, reduce drift risk
5. **#23–25 performance** (LEAK, Low) — free compute at low cost
6. **#1 proxy naming** (FRICTION, Trivial) — rename to `middleware.ts` for convention
7. **Remaining items** — batch by effort for efficient sprints

No data-corruption or crash bugs found. Core prediction/performance/replay data flows are sound.
