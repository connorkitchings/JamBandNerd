# Session Log: UI Polish, Bustouts/Debuts, and Fresh Predictions

**Date:** 2025-12-10  
**Session:** 04  
**Developer:** Codex (GPT-5)

---

## Task Completed

Refined the Streamlit UI/UX, added bustout/debut tagging to Last Show Analysis, and refreshed predictions (no ingestion).

## Key Outcomes

1) **Bustouts & Debuts**  
- Band-specific bustout thresholds (phish/um/wsp=50; others=25).  
- Debut detection now uses full prior setlist history; badges added for Debut and Bustout; bustout badge suppressed if the song was predicted.  
- Summary cards only show bustouts/debuts when present; grid tightened to fit one line.

2) **Prediction Display & Ranks**  
- Notebook predictor retains all songs/current_gap; UI hides recent (<=3) at display time and re-ranks afterward.  
- Prediction tables keep current_gap for bustout detection; setlist badges show Top10/25/50, Debut, Bustout.

3) **UI Styling & Performance Tab**  
- Polished cards, badges, and tables; centered chip values; mm/dd/yyyy date formatting on performance.  
- About tab restored with concise content.

4) **Fresh Predictions (no ingestion)**  
- Ran `scripts/generate_predictions.py` for all bands (goose, eggy, phish, wsp, billy, um) and models (notebook, ckplus).

## Blockers Encountered

None.

## Session Handoff & Next Steps

- Verify debut/bustout counts in the app (e.g., WSP 2025-11-23 shows 1 debut “Play a Train Song”; Goose 2025-12-08 shows 0 debuts).  
- If counts differ, check setlist ID mapping/caching; optionally add tooltips for badges.  
- Consider a hover tooltip for bustout/debut badges and optional CSV export on Predictions.

## Updated Documents

- `src/jambandnerd/web/components/tabs/last_show.py`
- `src/jambandnerd/web/components/tabs/predictions.py`
- `src/jambandnerd/web/components/tabs/performance.py`
- `src/jambandnerd/web/components/tabs/about.py`
- `src/jambandnerd/web/style.css`
- `src/jambandnerd/models/notebook/model.py`
- `docs/logs/2025-12-10/04_ui_polish_bustouts_debuts.md` (this log)
