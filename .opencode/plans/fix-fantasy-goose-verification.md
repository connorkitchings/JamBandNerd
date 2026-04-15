# Fix Fantasy Goose Post-Submission Verification

## Problem

`submit_entry()` in `fantasy_goose.py` fires `form.requestSubmit()` and waits only for `domcontentloaded`, then immediately navigates to My Picks and does a single string-match check. No retry, no delay, no diagnostic logging.

The failure: `RuntimeError: Fantasy Goose submission did not appear in My Picks for 04/14/2026 - War Memorial Auditorium - Fort Lauderdale, FL.`

## Root Causes

1. **Race condition** — zero delay between form submit and My Picks fetch; server may not have committed the entry yet
2. **Silent form rejection** — Alpine.js may not have reacted to the programmatic show-select `change` event before the hidden song inputs are filled, or the server may have returned a validation error that the code ignores
3. **No diagnostic output** — when the check fails, there's zero context about what the post-submit page or My Picks page actually contained

## Changes

All changes in `src/jambandnerd/integrations/fantasy_goose.py`.

### 1. `submit_entry()` — capture post-submit page for diagnostics

After `form.requestSubmit()` + `domcontentloaded`, capture the current page URL and body text before the caller navigates away. Return these as part of the result.

- Change `submit_entry()` to return a `(str, str)` tuple of `(current_url, body_text)` after submission
- This gives `run_fantasy_goose()` the ability to log what the server returned

### 2. `run_fantasy_goose()` — retry loop with delay for My Picks verification

Replace the single-shot check at lines 479-484 with:

```python
await submit_entry(page, show=target_show, picks=picks)
submit_url = page.url
submit_body = await page.locator("body").inner_text()

found = False
for attempt in range(3):
    await page.wait_for_timeout(2000)  # 2s delay between retries
    mypicks_text = await fetch_my_picks_text(page)
    if has_existing_entry(mypicks_text, target_show):
        found = True
        break

if not found:
    # Log diagnostics before raising
    print(f"Post-submit URL: {submit_url}")
    print(f"Post-submit body (first 500 chars): {submit_body[:500]}")
    print(f"My Picks body (first 500 chars): {mypicks_text[:500]}")
    raise RuntimeError(
        f"Fantasy Goose submission did not appear in My Picks "
        f"after 3 attempts for {target_show.label}."
    )
```

Key points:
- `submit_entry()` no longer needs to return anything extra — we read `page.url` and body text right after it returns
- 3 attempts with 2s delays = up to ~6s total wait, well within the 30-min workflow timeout
- Diagnostic logging prints the actual page content so CI failures are debuggable

### 3. `submit_entry()` — wait for navigation after form submit

Change the post-submit wait from `domcontentloaded` to `networkidle` to give the server more time to process and commit:

```python
# Before:
await page.wait_for_load_state("domcontentloaded")

# After:
await page.wait_for_load_state("networkidle")
```

This ensures the form POST response (including any redirects) is fully processed before we check the result.

### 4. `submit_entry()` — validate Alpine.js show selection propagated

Before filling hidden song inputs, add a short wait for Alpine.js to react to the show-select change:

```python
showSelect.value = String(showId);
showSelect.dispatchEvent(new Event('change', { bubbles: true }));

// Wait for Alpine to update song inputs for the selected show
await new Promise(resolve => setTimeout(resolve, 500));
```

This 500ms pause gives Alpine.js time to potentially re-render the hidden song inputs for the selected show before we overwrite them.

## Updated Tests

In `tests/test_fantasy_goose.py`, add tests for:

1. **Retry success on second attempt** — mock `fetch_my_picks_text` to return empty text first, then matching text second time. Verify the function succeeds without error.
2. **Retry exhaustion raises** — mock `fetch_my_picks_text` to always return empty text. Verify `RuntimeError` is raised after 3 attempts.
3. **Diagnostic output on failure** — verify that when retries are exhausted, the error message and stdout contain useful context.

Existing tests for `has_existing_entry` and `normalize_song_name` remain unchanged.

## Files Touched

| File | Change |
|------|--------|
| `src/jambandnerd/integrations/fantasy_goose.py` | Retry loop, diagnostic logging, networkidle wait, Alpine delay |
| `tests/test_fantasy_goose.py` | New tests for retry behavior |

## Risks

- The 500ms Alpine delay is a heuristic. If Alpine renders faster, it's wasted time. If slower, it won't help. But it's a safe bet given typical Alpine reactivity.
- The 2s retry delay is also a heuristic. Could be 1s or 3s. 2s is conservative without being wasteful.
- No fundamental architectural change — just hardening the verification step.
