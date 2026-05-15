# Mobile Verification Checklist

This checklist verifies the website in `apps/web` on real phones and tablets.

## 1) Run the website for mobile access

The default local verification path is the Next.js website. For real-device testing, bind the dev server to all interfaces and connect via your machine’s LAN IP.

```bash
npm install
npm run dev:web -- --hostname 0.0.0.0 --port 3000
```

Then open on your phone:

```text
http://<your-lan-ip>:3000
```

Notes:
- Your phone and laptop must be on the same network.
- If the page doesn’t load, verify macOS firewall settings and confirm the server is listening.

## 2) Core flows to verify (phone + tablet)

### Navigation and state
- Bottom navigation stays visible above the safe area.
- Active route styling updates correctly as you move between `/`, `/predictions`, `/performance`, `/last-show`, and `/about`.
- Band search params remain shareable and survive refresh.

### Homepage and prediction views
- Hero copy wraps cleanly on narrow widths.
- Dense tables remain horizontally scrollable instead of clipping.
- Filter controls stay tap-friendly and readable.

### Performance and last show
- Metric cards stack cleanly at narrow widths.
- Last-show detail route shows the mobile back affordance and remains readable.
- Setlist and retained prediction tables remain usable on touch screens.

## 3) Performance sanity checks

- First load per band can be slower (cache warmup); subsequent interactions should be fast.
- Switching routes should not trigger obvious client-side layout flicker.
- Server-rendered routes should not depend on client hydration for primary content.

## 4) If you hit a mobile-only bug

Capture:
- Device + browser (e.g., iPhone Safari 17, Pixel Chrome 131)
- URL (including query params)
- Band + selected date when relevant
- Screenshot (especially for layout issues)

Then reproduce on desktop with responsive emulation:
- Chrome DevTools → Toggle device toolbar → iPhone/Pixel presets.
