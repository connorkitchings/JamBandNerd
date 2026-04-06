# Session Log: 2026-03-24 - Prediction Hero Outlook Focus

## Goal

Remove model-comparison emphasis from the homepage hero and replace it with a clearer, more user-friendly explanation of what the current prediction board means.

## Constraints

- Keep the homepage hero forward-looking.
- Make `Show Outlook` understandable without requiring model-comparison context.
- Replace the unreliable native-title hover behavior with an explicit hover/focus explainer.

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed or artifacts produced

- `apps/web/src/components/prediction-hero.tsx`
- `apps/web/src/app/page.tsx`

## Validation status

- `npm run lint:web` passed.
- `npm run build:web` passed.

## Next step

- Review whether the Song Board should also de-emphasize secondary-model overlap icons now that the homepage hero no longer highlights model comparison.
