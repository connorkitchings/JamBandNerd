# Session Log: 2026-03-24 - Footer Versioning

## Goal

Add a visible JamBandNerd copyright/version marker to the website and document a simple versioning policy for future releases.

## Constraints

- Use the existing repo version instead of inventing a second public version.
- Keep the footer simple and unobtrusive.
- Document one clear bump policy that a non-engineer owner can follow.

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed or artifacts produced

- `apps/web/src/lib/site.ts`
- `apps/web/src/components/site-footer.tsx`
- `docs/operations/website_delivery.md`

## Validation status

- Pending

## Next step

- Decide whether to surface the same version string on `/about` or in deployment notes so users can verify what build is live.
