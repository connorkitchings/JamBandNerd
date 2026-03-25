# Website Delivery Strategy

This document defines the current delivery model for JamBandNerd: the website in `apps/web` is the
active product surface and operating path.

Current route split:

- `/` is the public homepage and product entry page
- `/predictions` is the primary live dashboard for repeat use
- `/performance`, `/compare`, and `/replay` are the three historical analysis surfaces
- `/?band=...&model=...` redirects to `/predictions?...` for compatibility

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
- **Search-param navigation**: prefer URL-driven band/model/date state so pages are shareable and hydration stays light.
- **Freshness over static caching**: prediction and replay routes should favor dynamic server rendering while the marketing shell can stay static later.

## Visual Source Of Truth

- **Primary design input**: Google Stitch exports are the current visual source of truth for the website dashboard.
- **Integration rule**: translate Stitch HTML/Tailwind exports into typed React components rather than pasting opaque static markup directly into route files.
- **Product rule**: replace Stitch placeholder entities with real JamBandNerd-supported bands, models, and routes before shipping UI work.
- **Mobile rule**: preserve Stitch layout intent, but adapt navigation and dense modules for touch targets, fixed-bottom nav, and horizontal-scroll-safe tables.

## Product Direction

The website should become the primary public surface for:

- Multi-band prediction browsing
- Model comparison
- Replay workflows
- Venue-specific historical analytics
- Accuracy and performance views
- Last-show details and explanatory content

The website is now the default local, contributor-facing, and public product surface. Remaining
work is deployment hardening, hosted verification, and product refinement on the live website.

## Operating Constraints

- Keep `scripts/run_optimized_pipeline.py` as the canonical pipeline entrypoint.
- Preserve existing Supabase prediction and accuracy tables unless the website exposes a real gap.
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
cp apps/web/.env.local.example apps/web/.env.local
npm run dev:web
npm run lint:web
npm run build:web
npm run test:web:smoke
```

## Release Versioning

JamBandNerd should use a single public product version across the repo and website.

- Current public version: `0.1.0`
- Versioning style: Semantic Versioning (`MAJOR.MINOR.PATCH`)
- Scope rule: keep `pyproject.toml`, `src/jambandnerd/__init__.py`, `apps/web/package.json`, and the website footer version in sync

Use these bump rules:

- Patch (`0.1.x`): UI polish, bug fixes, copy edits, test-only work, and non-breaking internal cleanup
- Minor (`0.x.0`): new user-facing pages/features, notable analytics additions, or meaningful model/product improvements that do not break expected workflows
- Major (`x.0.0`): breaking product changes, major route/navigation resets, incompatible data contracts, or the first stable public `1.0.0`

Until the product is stable, stay on the `0.x` line. Treat `0.1.0` as the first visible website version rather than a finished general-availability release.

## Environment Variables

The website currently expects the same two server-side variables in all environments:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

For local development, copy `apps/web/.env.local.example` to `apps/web/.env.local`.

Do not use a service-role key in the website environment.

For Vercel, add the same variable names to:

- Preview
- Production

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

1. `npm run lint:web`
2. `npm run build:web`
3. `npm run test:web:smoke`
4. `Hosted Website Smoke` for deployed preview or production URLs when you need hosted verification

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
- `/replay`
- `/venues`
- `/compare`
- `/performance`
- `/last-show`

Also confirm that pages render with server-side Supabase reads instead of the missing-env fallback state.

The smoke test suite also covers `/about` and `/predictions` alongside the routes above.
