# Frontend Strategy

This document defines the frontend strategy for JamBandNerd, complementing the existing
[Data Strategy](../reference/specifications/data_strategy.md) and Backend Strategy. It covers
how the website communicates predictions to users, UI/UX principles, component conventions,
accessibility standards, and the data contract between Supabase and the frontend.

---

## Purpose

JamBandNerd predicts jam band setlists using gap-based and frequency-based models. The
website is the primary public surface for browsing these predictions, exploring historical
data, and tracking model accuracy.

The core challenge: **predictions are probabilistic signals, not certain outcomes.** The
frontend must communicate this honestly while remaining engaging and useful.

---

## Core Principles

### Uncertainty Transparency

Every prediction is a likelihood ranking, not a guarantee. The UI must reinforce this at
every level:

- **In-UI disclaimers** appear alongside predictions, not just in the FAQ.
- **Tier labels** are descriptive but not definitive.
- **Accuracy metrics** are shown with context (comparison to baselines).
- **Show Outlook** labels are clearly heuristic — fun, but fallible.

### Mobile First

The primary audience uses phones during shows or commuting. Desktop is secondary.

- Touch targets minimum 44×44px.
- Bottom navigation on mobile, side nav on desktop.
- Tables scroll horizontally rather than wrapping awkwardly.
- Safe-area insets respected for notched devices.

### Server First

Minimize client JavaScript. Leverage Supabase server-side reads for fast initial loads.

- Core routes use Server Components and server-side Supabase queries.
- Client state kept minimal (search, collapsible sections).
- No heavy charting libraries unless clearly justified.
- URL-driven state for shareable views.

### Narrative + Data

Combine algorithmic output with plain-language context.

- **Show Outlook** labels summarize the prediction board's character.
- **Model Agreement** breakdown shows how confidently models agree.
- **Accuracy page** contextualizes recall with baseline comparisons.
- Explanatory copy helps users understand what they're looking at.

### Progressive Disclosure

Show summary context first. Allow users to drill into details.

- Song board starts collapsed by tier (Expected/Hot open, Likely/Possible collapsed).
- Accuracy charts hide raw data behind a visual.
- "How to read this" expandables on dense pages.
- Tooltips on technical terms and labels.

---

## Information Architecture

### Page Inventory

| Route | Purpose | Primary Uncertainty Element |
|-------|---------|---------------------------|
| `/` | Next-show predictions dashboard | Show Outlook, Model Agreement, Track Record |
| `/replay` | Historical prediction replay | Shared show context, both model boards, Predicted vs Actual overlay |
| `/compare` | Model comparison side-by-side | Tier alignment, agreement breakdown |
| `/performance` | Accuracy tracking | Recall percentages, trend deltas, baseline comparisons |
| `/last-show` | Most recent completed show | Predicted vs Actual, accuracy for that show |
| `/about` | Education and explanation | FAQ, model explainers, pipeline overview |
| `/predictions` | Raw prediction table view | Per-song tier and gap data |

### Navigation

- **Compatibility**: `/explorer` redirects to `/replay`; it is not a primary product surface.
- **Mobile**: Fixed bottom nav with 5 items (Home, Compare, Performance, Replay, Predict)
- **Desktop**: Side navigation with full labels
- **State**: URL-driven via search params (`?band=goose&model=ckplus`)
- **Search**: Global search in header; song-specific search on song board
- **Analysis routes**: Replay and Compare share the same navigation grouping

---

## Uncertainty Communication Framework

### Layered Display

Predictions are communicated through stacked layers, each reinforcing uncertainty:

| Layer | What it shows | How uncertainty is communicated |
|-------|---------------|-------------------------------|
| **Hero summary** | Show Outlook label | Narrative label signals model consensus; tooltip explains logic |
| **Tier badges** | Expected / Hot / Likely / Possible | Tooltip: "Based on rank position, not probability" |
| **Song board** | Ranked songs with gap | Footer disclaimer: "Ranks reflect relative likelihood" |
| **Model Agreement** | % match across models | Tiered breakdown (top-10/25/50) with weighted composite |
| **Track Record** | Historical recall | "X% top-10 recall across Y scored shows" |

### Tier System

Tiers are rank-based heuristics, not probabilistic buckets. They communicate relative
likelihood within the ranked list.

| Tier | Rank Range | Display | Tooltip text |
|------|-----------|---------|--------------|
| Expected | 1–5 | Yellow badge | "Strongest rotation signal — high recent activity and model confidence" |
| Hot | 6–15 | Blue badge | "Solid candidate — one or both models rank this song highly" |
| Likely | 16–30 | Gray badge | "In the pool with a moderate signal" |
| Possible | 31+ | Gold badge | "Lower recent activity — could still appear" |

Tiers are computed in `computeTier()` (`apps/web/src/lib/data.ts`). When probability
scores are available from models, tiers will be probability-based instead.

### Show Outlook

Show Outlook is a heuristic label describing the predicted character of the upcoming show
based on the top-10 predictions. It is intended to be fun and informative, not precise.

**Labels:**

| Label | Trigger | Tooltip |
|-------|---------|---------|
| Deep cuts expected | Avg recent gap ≥ 15 shows | "Top predictions have high gaps — model favors less-played songs" |
| Heavy rotation | ≥4 hot-tier songs AND avg recent gap < 8 | "Top predictions are frequently-played songs" |
| Bust-out potential | >40% of all songs in possible tier | "Model sees potential for rare songs to appear" |
| Balanced expectations | Default | "Mixed signals — no strong pattern detected" |

The label is computed client-side in `getOutlookLabel()` (`prediction-hero.tsx`).

### Model Agreement

When a secondary model is available, agreement is shown as:

- **Badge**: Weighted composite percentage (e.g., "71% Match")
- **Breakdown**: Match counts for top-10, top-25, and top-50

The composite score weights top-10 matches 2× and others 1×. The formula:

```
composite = (top10_matches × 2 + top25_matches + top50_matches) / (10×2 + 25 + 50)
```

Implementation in `calculateModelAgreement()` (`apps/web/src/lib/data.ts`).

### Model Agreement Icons

On the song board, songs predicted by both models show a **both-models icon**. This
provides at-a-glance consensus signal without exposing raw probabilities.

---

## Component Conventions

### Shared Components

| Component | Purpose | Key props |
|-----------|---------|-----------|
| `SectionCard` | Bounded content section with title/eyebrow | `title`, `eyebrow`, `children` |
| `TierBadge` | Colored badge for tier labels | `tier`, `showDescription` |
| `SongBoard` | Ranked prediction table | `rows`, `highlightSongs`, `secondarySongs`, `compact` |
| `TierSection` | Collapsible tier group in SongBoard | `tier`, `rows`, `highlightSongs`, `secondarySongs` |
| `AccuracyTable` | Per-show recall metrics | `rows` |
| `RecallChart` | SVG line chart of recall over time | `rows` |
| `SetlistTable` | Song list with set/position | `songs`, `highlightSongs` |
| `PredictionHero` | Hero section with venue, date, stats | Venue, date, model, agreement, outlook |
| `SongSearch` | Song-specific search within board | `songs` |
| `FilterLinks` | Band/model filter navigation | `pathname`, `band`, `model`, `bands` |
| `DataState` | Empty/error/missing-env states | `title`, `body` |
| `SectionCard` | Bounded content section | `title`, `eyebrow`, `children` |
| `DashboardSideNav` | Desktop side navigation | `band`, `model`, `bands` |
| `MobileBottomNav` | Mobile bottom navigation | — |

### Visual Design Tokens

Defined in `globals.css`:

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#b0c6ff` | Accent elements, links, active states |
| Primary container | `#0058cb` | Gradient backgrounds |
| Secondary container | `#334d58` | Eyebrow badges |
| Tertiary | `#e9c400` | Model agreement icons |
| Background/Surface | `#111316` | Page background |
| Surface container low | `#1a1c1f` | Card backgrounds |
| On surface | `#e2e2e6` | Primary text |
| On surface variant | `#c3c6d6` | Secondary text |
| Outline variant | `#424654` | Borders, dividers |
| Tier expected | `#f59e0b` / `#451a03` | Expected tier |
| Tier hot | `#60a5fa` / `#172554` | Hot tier |
| Tier likely | `#8d90a0` / `#1e2023` | Likely tier |
| Tier possible | `#e9c400` / `#332d00` | Possible tier |

**Typography:**
- Headings: Space Grotesk (bold, uppercase with tight tracking)
- Labels: Space Grotesk (small, uppercase with wide tracking)
- Body: Inter (readable, neutral)

**Spacing:** 4px base unit. Padding typically 16px (mobile) / 24–32px (desktop).

---

## Accessibility Standards

The website targets [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines)
(WIG) compliance. Key requirements:

### Focus States

- All interactive elements have visible focus styles (`focus-visible:ring-2`).
- No `outline: none` without a focus-visible replacement.
- Use `:focus-visible` over `:focus` (avoid focus ring on click).

### Reduced Motion

Animations and transitions honor `prefers-reduced-motion`. CSS in `globals.css` provides
a media query to disable or reduce motion for users who prefer it.

### Keyboard Navigation

- Skip-to-content link at the top of each page.
- Interactive elements reachable via Tab.
- Collapsible sections have `aria-expanded` and `aria-controls`.
- `<button>` used for actions; `<a>`/`<Link>` used for navigation.

### Semantic HTML

- Headings follow hierarchy (`h1` → `h2` → `h3`).
- `<details>`/`<summary>` used for FAQ accordions.
- `<table>` used for data tables.
- Icon-only buttons have `aria-label`.
- Images have `alt` text or `alt=""` if decorative.

### Color and Contrast

- Text contrast ratios meet WCAG AA (4.5:1 for body, 3:1 for large text).
- Color is not the sole means of conveying information (icons + color for tiers).
- Dark mode uses `color-scheme: dark` on `<html>`.

---

## Frontend Data Contract

### Supabase Tables

The frontend reads from these Supabase tables:

| Table | Purpose |
|-------|---------|
| `predictions` | Canonical run-level prediction rows keyed by `band`, `model_slug`, `reference_date`, and `model_version` |
| `prediction_songs` | Projection view of latest predictions per band/model |
| `accuracy_per_show` | Per-show accuracy metrics keyed by band/model_version |
| `historical_prediction_runs` | Replay lineage linking scored boards to completed shows |

### Prediction Row Schema

Each prediction row in the frontend (`PredictionRow` type) contains:

| Field | Source | Description |
|-------|--------|-------------|
| `rank` | `rank` | Position in ranked list (1-indexed) |
| `songName` | `song_name` | Song name |
| `lastPlayed` | `LTP` / `last_played_date` | ISO date of last play |
| `currentGap` | `current_gap` | Shows since last performance |
| `playsPastYear` | `plays_past_year` | Unique shows in past 365 days |
| `avgGap` | `avg_gap` | All-time average gap between plays |
| `recentAvgGap` | `recent_avg_gap` | Average gap over last 25 plays |
| `gapRatio` | `gap_ratio` | `current_gap / avg_gap` |
| `gapZScore` | `gap_z_score` | Z-score of current gap vs history |
| `ckplusScore` | `ckplus_score` | CK+ model composite score |
| `probability` | `probability` | Model probability (future; currently null) |
| `tier` | computed | `expected` / `hot` / `likely` / `possible` |

### Accuracy Row Schema

Each accuracy row (`AccuracyRow` type):

| Field | Source | Description |
|-------|--------|-------------|
| `showDate` | `show_date` | ISO date of the scored show |
| `venueName` | `venue_name` | Venue of the scored show |
| `k10Recall` | `k10_recall` | Fraction of top-10 predictions that appeared |
| `k25Recall` | `k25_recall` | Fraction of top-25 predictions that appeared |
| `k50Recall` | `k50_recall` | Fraction of top-50 predictions that appeared |

---

## Model Definitions

### Notebook Model

Frequency-based model focused on songs active in the recent rotation while excluding the
last three shows.

| Field | Description |
|-------|-------------|
| Primary signal | `plays_past_year` (songs played most in the last 12 months) |
| Tiebreaker | `current_gap` (higher gap wins) |
| Exclusion | Songs played in the last 3 shows |

### CK+ Model

Gap-based model that ranks songs by how overdue they are relative to their historical
cadence.

| Field | Description |
|-------|-------------|
| Primary signal | `ckplus_score` (composite of gap_ratio and gap_z_score) |
| Score components | `avg_gap`, `recent_avg_gap`, `gap_ratio`, `gap_z_score` |
| Exclusion | Songs played in the last 3 shows |
| Retirement | Songs exceeding band-specific gap thresholds (e.g., 100 for Goose, 150 for Phish) |

---

## Performance Considerations

- **Lists > 50 items**: Song board tiers are collapsible, reducing visible DOM.
- **Images**: All images use `loading="lazy"` except above-fold critical images.
- **Fonts**: Google Fonts loaded via `next/font/google` with `display: swap`.
- **Data fetching**: Supabase queries are server-side, cached with React `cache()`, and
  invalidated via `force-dynamic` on prediction routes.
- **Build**: TypeScript strict mode enabled; lint runs before build.
