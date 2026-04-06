# Session Log: 2026-03-25 - Compare and Deep-Dive Selector Unification

## Goal

Unify `/compare` and `/explorer` around the same shared selector pattern used by
the other product pages, and remove the old stacked `Tab` row from the compare /
explorer navigation path.

## Constraints

- Keep the stronger shared band-selector treatment used on predictions and performance
- Replace `Tab` with `View`
- Preserve route-specific query state where the selector needs it

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed

- `apps/web/src/app/compare/page.tsx`
- `apps/web/src/app/explorer/page.tsx`
- `apps/web/src/components/dashboard-side-nav.tsx`
- `apps/web/src/components/filter-links.tsx`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed

## Notes

- `/compare` now uses `DashboardSideNav` instead of `FilterLinks`
- both `/compare` and `/explorer` use `View` as the right-hand selector label
- the compare/explorer-specific stacked `Tab` row was removed from `FilterLinks`
- `DashboardSideNav` now supports custom `bandLinks` so compare/explorer can preserve
  route-specific query params instead of falling back to predictions-style model links
