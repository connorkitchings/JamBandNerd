# Mobile Verification Checklist (Streamlit)

This checklist helps verify the Streamlit UI on real phones/tablets after UI or data changes.

## 1) Run the app for mobile access

The repo default binds Streamlit to `localhost` (see `.streamlit/config.toml`). For real-device
testing, bind to all interfaces and connect via your machine’s LAN IP.

```bash
# Bind to 0.0.0.0 so your phone can reach it on the local network
uv run streamlit run src/jambandnerd/web/app.py --server.address 0.0.0.0 --server.port 8501
```

Then open on your phone:

```text
http://<your-lan-ip>:8501
```

Notes:
- Your phone and laptop must be on the same network.
- If the page doesn’t load, verify macOS firewall settings and confirm the server is listening.

## 2) Core flows to verify (phone + tablet)

### Navigation and state
- Band selector changes on the first tap (no “double-click” required).
- Model selector changes persist across tab switches.
- Query params (if used) reflect current band/model and restore on refresh.

### Predictions tab
- Tables are horizontally scrollable (no content cut off).
- Top-K badges render correctly and remain readable.
- “Loading” spinners appear during fetches and disappear reliably.

### Last Show Analysis tab
- Hero/header section wraps cleanly and doesn’t overflow.
- Summary cards stack to a single column and remain readable.
- Setlist rows show the correct badges (Top10/25/50, Debut, Bustout where applicable).

### Historical Explorer tab
- Date dropdown is responsive and only lists dates with predictions available.
- “Predicted At” shows a real timestamp (not “N/A”) when metadata exists.
- For a known historical show, hits highlight correctly vs the actual setlist.

### Performance / Leaderboard tabs
- Charts are readable at narrow widths (labels/tooltips usable).
- Tooltips don’t obscure the entire chart area on tap.

## 3) Performance sanity checks

- First load per band/model can be slower (cache warmup); subsequent interactions should be fast.
- Switching tabs should not re-fetch large tables repeatedly.

## 4) If you hit a mobile-only bug

Capture:
- Device + browser (e.g., iPhone Safari 17, Pixel Chrome 131)
- URL (including query params)
- Band + model + tab + selected date (if Explorer)
- Screenshot (especially for layout issues)

Then reproduce on desktop with responsive emulation:
- Chrome DevTools → Toggle device toolbar → iPhone/Pixel presets.
