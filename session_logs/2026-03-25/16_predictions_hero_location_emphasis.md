# Session Log: 2026-03-25 - Predictions Hero Location Emphasis

## Goal

Shift the visual emphasis in the predictions hero from venue name to city/state so the next-show box reads more immediately by location.

## Constraints

- Keep the existing data contract and props intact
- Preserve a sane fallback when location data is missing
- Limit the change to presentation on the predictions page

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed

- `apps/web/src/components/prediction-hero.tsx`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next step

Continue the predictions-page polish pass and review any remaining hierarchy issues in the hero and song board.
