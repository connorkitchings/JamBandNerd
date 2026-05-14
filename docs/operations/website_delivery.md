# Website Delivery Strategy

This document defines the current delivery model for JamBandNerd: the website in `apps/web` is the
active product surface and operating path.

Current route split:

- `/` is the public homepage and product entry page
- `/predictions` is the primary live dashboard for repeat use
- `/performance` is the historical accuracy surface
- `/last-show` is the most recent completed-show detail surface
- `/about`, `/contact`, and `/data-use` are public informational routes
- `/?band=...` redirects to `/predictions?band=...` for compatibility

## Target Architecture

- **Frontend**: Monorepo website application
- **Framework target**: Next.js
- **Hosting target**: Vercel
- **Data access**: Server-side reads from Supabase
- **API strategy**: No separate public API in v1

## Optimization Defaults

- **Server first**: default to Server Components and server-side Supabase reads for core routes.
- **Minimal client JavaScript**: avoid client state and heavy UI/charting libraries until they are clearly needed.
- **Mobile first**: design for small screens first, then expand to tablet/desktop layouts.
- **Safe-area aware**: bottom navigation and page content must respect mobile safe-area insets.
- **Overflow safe**: data tables and dense views must remain usable on phones through scroll-safe wrappers rather than clipped content.
- **Shared dense-data pattern**: tables and long data grids should use a single responsive wrapper/padding pattern instead of route-specific one-offs.
- **Search-param navigation**: prefer URL-driven band state so pages are shareable and hydration stays light.
- **Freshness over static caching**: prediction and performance routes should favor dynamic server rendering while the marketing shell can stay static later.
- **Hermetic builds**: prefer local assets and system fallbacks over build-time network fetches.

## Web Module Ownership

- `apps/web/src/app/**`: route composition, metadata, and search-param handling
- `apps/web/src/components/**`: reusable presentation and client islands
- `apps/web/src/lib/data.ts`: compatibility barrel for existing route imports
- `apps/web/src/lib/data/bands.ts`: band discovery and selection helpers
- `apps/web/src/lib/data/predictions.ts`: latest/current prediction reads
- `apps/web/src/lib/data/accuracy.ts`: historical accuracy reads
- `apps/web/src/lib/data/shows.ts`: show detail, next show, and setlist reads

Client component rule:
- Keep route-level Supabase reads on the server. Use `"use client"` only for interactive islands, navigation hooks, or live subscriptions.

## Visual Source Of Truth

- **Primary design input**: Google Stitch exports are the current visual source of truth for the website dashboard.
- **Integration rule**: translate Stitch HTML/Tailwind exports into typed React components rather than pasting opaque static markup directly into route files.
- **Product rule**: replace Stitch placeholder entities with real JamBandNerd-supported bands and routes before shipping UI work.
- **Mobile rule**: preserve Stitch layout intent, but adapt navigation and dense modules for touch targets, fixed-bottom nav, and horizontal-scroll-safe tables.

## Product Direction

The website should become the primary public surface for:

- Multi-band prediction browsing
- Accuracy and performance views
- Last-show details and explanatory content

The website is now the default local, contributor-facing, and public product surface. Remaining
work is deployment hardening, hosted verification, and product refinement on the live website.

## Operating Constraints

- Keep `scripts/run_optimized_pipeline.py` as the canonical pipeline entrypoint.
- Preserve the single-model `setlist_*` Supabase prediction and accuracy contract unless the website exposes a real gap.
- Avoid introducing a public API unless external-consumer requirements justify it later.
- Do not reintroduce Streamlit-specific guidance into primary onboarding or operations docs.

## Current Priorities

1. Keep the website routes and shared shell production-ready.
2. Make the website the default path in docs, onboarding, and workflow messaging.
3. Harden Vercel deployment, preview verification, and production env management.
4. Revisit public API work only after the website creates real external-consumer demand.

## Branch Strategy

- **Production branch**: `main`
- **Preview branches**: every non-`main` branch and pull request
- **Current state**: GitHub default branch and `origin/HEAD` now point to `main`

## Current Local Commands

```bash
npm install
npx playwright install --with-deps chromium
cp apps/web/.env.local.example apps/web/.env.local
npm run dev:web
npm run verify:web
```

## Release Versioning

JamBandNerd should use a single public product version across the repo and website.

- Current public version: `0.3.0`
- Versioning style: Semantic Versioning (`MAJOR.MINOR.PATCH`)
- Scope rule: keep `pyproject.toml`, `src/jambandnerd/__init__.py`, `apps/web/package.json`, and the website footer version in sync

Use these bump rules:

- Patch (`0.2.x`): UI polish, bug fixes, copy edits, test-only work, and non-breaking internal cleanup
- Minor (`0.x.0`): new user-facing pages/features, notable analytics additions, or meaningful model/product improvements that do not break expected workflows
- Major (`x.0.0`): breaking product changes, major route/navigation resets, incompatible data contracts, or the first stable public `1.0.0`

Until the product is stable, stay on the `0.x` line. Treat `0.3.0` as the current visible website version rather than a finished general-availability release.

## Environment Variables

The website currently expects the same two server-side variables in all environments:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

For local development, copy `apps/web/.env.local.example` to `apps/web/.env.local`.

Do not use a service-role key in the website environment.

For Vercel, add the same variable names to:

- Preview
- Production

The internal admin setlist tooling additionally expects:

- `ADMIN_PASSWORD`
- `ADMIN_SESSION_SECRET`

The admin route now authenticates into an httpOnly cookie-backed session instead of sending bearer credentials with browser-side write requests.

## Vercel Project Setup

Use Vercel’s native GitHub integration rather than a repo-driven deploy action.

Recommended project settings:

- **Repository**: `connorkitchings/JamBandNerd`
- **Root Directory**: `apps/web`
- **Framework Preset**: Next.js
- **Install / build settings**: use Vercel defaults after setting the root directory; only override if workspace auto-detection fails
- **Production Branch**: `main`

## GitHub Verification Flow

The repo should verify the website in GitHub Actions before relying on Vercel previews:

1. `npm run verify:web`
2. `npm run verify:clean`
3. `Hosted Website Smoke` for deployed preview or production URLs when you need hosted verification

This keeps deployment triggering in Vercel while GitHub Actions acts as the verification gate.

For Vercel preview URLs protected by Deployment Protection, configure the
`VERCEL_PROTECTION_BYPASS_TOKEN` GitHub secret and let the hosted smoke workflow
bootstrap the preview URL with Vercel's documented bypass query parameters
before running the normal route assertions.

## Deployment Expectations

- Preview deployments for pull requests/branches
- Production deployment on the main website branch
- Runtime secrets for Supabase configured through the hosting platform
- Basic health checks and deploy verification as part of website operations
- Pull request validation through GitHub Actions before `main` promotion

## Post-Deploy Verification

After a preview or production deploy, run hosted smoke verification against the deployed URL:

```bash
SMOKE_BASE_URL=https://jambandnerd.com npm run test:web:smoke:hosted
```

For a protected preview deployment, provide the bypass token in the environment:

```bash
SMOKE_BASE_URL=https://your-preview-url.vercel.app \
VERCEL_PROTECTION_BYPASS_TOKEN=your-bypass-secret \
npm run test:web:smoke:hosted
```

Use the `Hosted Website Smoke` GitHub Actions workflow for scheduled production
checks or ad hoc preview verification by overriding the `base_url` workflow
input. Preview workflow runs require the `VERCEL_PROTECTION_BYPASS_TOKEN`
GitHub secret.

After smoke verification, manually verify:

- `/`
- `/predictions`
- `/performance`
- `/last-show`
- `/about`
- `/contact`
- `/data-use`

Also confirm that pages render with server-side Supabase reads instead of the missing-env fallback state.

The smoke test suite also confirms removed multi-model routes stay unavailable.

See [Main Branch Elevation](./main_branch_elevation.md) for the documented `main` branch promotion gate.
