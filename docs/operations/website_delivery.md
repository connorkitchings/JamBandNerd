# Website Delivery Strategy

This document defines the current product target for JamBandNerd: the website in `apps/web`, not
the legacy Streamlit deployment.

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
- **Freshness over static caching**: prediction and explorer routes should favor dynamic server rendering while the marketing shell can stay static later.

## Visual Source Of Truth

- **Primary design input**: Google Stitch exports are the current visual source of truth for the website dashboard.
- **Integration rule**: translate Stitch HTML/Tailwind exports into typed React components rather than pasting opaque static markup directly into route files.
- **Product rule**: replace Stitch placeholder entities with real JamBandNerd-supported bands, models, and routes before shipping UI work.
- **Mobile rule**: preserve Stitch layout intent, but adapt navigation and dense modules for touch targets, fixed-bottom nav, and horizontal-scroll-safe tables.

## Product Direction

The website should become the primary public surface for:

- Multi-band prediction browsing
- Model comparison
- Historical explorer workflows
- Accuracy and performance views
- Last-show details and explanatory content

The website is now the default local and contributor-facing product surface. Remaining work is deployment hardening, final cutover, and eventual removal of the Streamlit fallback.

## Migration Constraints

- Keep `scripts/run_optimized_pipeline.py` as the canonical pipeline entrypoint.
- Preserve existing Supabase prediction and accuracy tables unless the website exposes a real gap.
- Treat the current Streamlit app as a legacy transition surface, not the destination architecture.
- Avoid introducing a public API unless external-consumer requirements justify it later.
- Keep legacy Streamlit run instructions out of primary onboarding docs.

## Delivery Order

1. Keep the website routes and shared shell production-ready.
2. Make the website the default path in docs, onboarding, and workflow messaging.
3. Harden Vercel deployment, preview verification, and production env management.
4. Remove Streamlit from the primary operations path, then retire the fallback code in a later phase.

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

## Environment Variables

The website currently expects the same two server-side variables in all environments:

- `SUPABASE_URL`
- `SUPABASE_KEY`

For local development, copy `apps/web/.env.local.example` to `apps/web/.env.local`.

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
3. `npm run test:web:smoke:list`

This keeps deployment triggering in Vercel while GitHub Actions acts as the verification gate.

## Deployment Expectations

- Preview deployments for pull requests/branches
- Production deployment on the main website branch
- Runtime secrets for Supabase configured through the hosting platform
- Basic health checks and deploy verification as part of website operations

## Post-Deploy Verification

After a preview or production deploy, manually verify:

- `/`
- `/explorer`
- `/compare`
- `/performance`
- `/last-show`

Also confirm that pages render with server-side Supabase reads instead of the missing-env fallback state.
