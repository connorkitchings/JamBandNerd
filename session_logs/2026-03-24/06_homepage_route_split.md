# Session Log: 2026-03-24 - Homepage Route Split

## Goal

Introduce a real homepage at `/` and move the full prediction dashboard to `/predictions`.

## Constraints

- Keep old shared query links working.
- Do not duplicate the full dashboard on the homepage.
- Preserve the website-first route structure and existing navigation model.

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed or artifacts produced

- `apps/web/src/app/page.tsx`
- `apps/web/src/app/predictions/page.tsx`
- `apps/web/src/lib/navigation.ts`
- `apps/web/src/components/site-header.tsx`
- `apps/web/src/app/about/page.tsx`
- `apps/web/src/app/last-show/page.tsx`
- `apps/web/tests/smoke/public-shell.spec.ts`
- `docs/operations/website_delivery.md`

## Validation status

- `npm run lint:web` passed.
- `npm run build:web` passed.
- `npm run test:web:smoke` did not execute assertions because Playwright Chromium aborted on launch in this environment.

## Next step

- Review whether the homepage should eventually get a dedicated Home nav item or stay logo-only.
