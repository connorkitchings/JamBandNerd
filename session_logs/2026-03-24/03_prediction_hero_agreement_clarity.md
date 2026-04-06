# Session Log: 2026-03-24 - Prediction Hero Agreement Clarity

## Goal

Make the prediction hero's model-overlap language user-friendly and ensure the overlap math matches the wording shown in the UI.

## Constraints

- Keep the prediction hero forward-looking.
- Avoid introducing score/performance language into the current prediction card.
- Preserve the existing two-model comparison concept while clarifying what the counts mean.

## Commands run

- `node --test --experimental-strip-types apps/web/tests/unit/model-agreement.test.ts apps/web/tests/unit/venue-analytics.test.ts`
- `npm run lint:web`
- `npm run build:web`

## Files changed or artifacts produced

- `apps/web/src/lib/model-agreement.ts`
- `apps/web/src/lib/data.ts`
- `apps/web/src/components/prediction-hero.tsx`
- `apps/web/tests/unit/model-agreement.test.ts`

## Validation status

- Pure agreement and venue helper tests passed.
- `npm run lint:web` passed.
- `npm run build:web` passed.

## Next step

- Review the prediction hero language on a few bands and decide whether `Show Outlook` itself should also be renamed to a less analytical phrase such as `Next Show Read`.
