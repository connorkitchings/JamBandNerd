# Website Delivery Strategy

This document defines the new product target for JamBandNerd: a full website rather than a
Streamlit deployment.

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
- **Overflow safe**: data tables and dense views must remain usable on phones through scroll-safe wrappers rather than clipped content.
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

The goal is feature parity with the current Streamlit experience before cutover.

## Migration Constraints

- Keep `scripts/run_optimized_pipeline.py` as the canonical pipeline entrypoint.
- Preserve existing Supabase prediction and accuracy tables unless the website exposes a real gap.
- Treat the current Streamlit app as a legacy transition surface, not the destination architecture.
- Avoid introducing a public API unless external-consumer requirements justify it later.

## Delivery Order

1. Align active documentation with the website-first direction.
2. Scaffold the website app in this repository.
3. Rebuild the current user-facing product surface on the website.
4. Cut over the public product and demote Streamlit to legacy/internal use.

## Current Local Commands

```bash
npm install
npm run dev:web
npm run build:web
```

## Deployment Expectations

- Preview deployments for pull requests/branches
- Production deployment on the main website branch
- Runtime secrets for Supabase configured through the hosting platform
- Basic health checks and deploy verification as part of website operations
