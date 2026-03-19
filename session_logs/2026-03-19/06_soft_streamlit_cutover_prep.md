# 2026-03-19 Session Log 06

## Goal

Implement a soft Streamlit cutover pass so the website becomes the default JamBandNerd product surface in active docs and workflow messaging, while keeping Streamlit available as a temporary fallback.

## Constraints

- Keep the legacy Streamlit code and dependency in place for one more phase.
- Remove Streamlit from primary onboarding and operations guidance.
- Do not invent a production website URL if the final deployment URL is not locked yet.
- Keep website-facing copy aligned with the current `apps/web` reality.

## Commands Run

- `git branch --show-current`
- `git status --short`
- `sed -n ...` on active docs, website pages, and `.github/workflows/daily-pipeline.yml`
- `rg -n ...` for Streamlit references and workflow messaging
- `npm run lint:web`
- `npm run build:web`
- `rg -n "streamlit run src/jambandnerd/web/app.py|jambandnerd.streamlit.app" ...`

## Files Changed Or Artifacts Produced

- Rewrote primary README and user docs so the website commands are the default UI path.
- Updated contributor/extensibility docs to target `apps/web` for presentation-layer changes.
- Reframed website delivery, mobile verification, and legacy Streamlit ops docs around a soft-cutover model.
- Updated the roadmap, implementation status, docs index, and website About page to reflect the current state.
- Removed the Streamlit Cloud link from the daily pipeline GitHub Actions summary in favor of neutral website wording.

## Validation Status

- `npm run lint:web`: passed
- `npm run build:web`: passed
- Stale-reference grep for `streamlit run src/jambandnerd/web/app.py` and `jambandnerd.streamlit.app`: only legacy fallback/troubleshooting docs remain

## Next Step

Add deployment hardening for the website so the new default product surface also has a clear preview and production operations path.
