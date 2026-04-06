# Session Log: 2026-03-24 - Predictions Page Next Show Focus

## Goal

Make the predictions homepage hero forward-looking by showing the next show instead of reading as a backward-looking latest scored snapshot.

## Constraints

- Keep the existing prediction snapshot data model intact.
- Change only the homepage hero context, not Explorer or Last Show behavior.
- Fall back gracefully when no upcoming show exists in the band's raw shows table.

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed or artifacts produced

- `apps/web/src/lib/data.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/components/prediction-hero.tsx`

## Validation status

- `npm run lint:web` passed.
- `npm run build:web` passed.

## Next step

- Review the live homepage for each band and decide whether bands without future show rows should show a stronger fallback label than `Prediction Outlook`.
