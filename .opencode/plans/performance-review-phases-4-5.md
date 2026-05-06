# Performance Review — Phases 4-5: Medium & Low Priority Items

**Date:** 2026-05-06
**Scope:** M1-M7 (all medium and low priority items from performance review)

---

## M1: Fix Silent Error Swallowing in `common.py`

### Problem
`upsert_table()` catches exceptions and returns silently — failed upserts are ignored. Callers have no way to know if the operation succeeded.

### Fix
Change return type from `None` to `bool`. Return `True` on success, `False` on failure.

### File: `scripts/common.py` (lines 22-61)

**Before:**
```python
def upsert_table(...) -> None:
    ...
    except Exception as e:
        log(f"Error collecting {table_name}: {e}")
        return  # Silent failure
    ...
    except Exception as e:
        log(f"Error upserting to {table_name}: {e}")  # Silent failure
```

**After:**
```python
def upsert_table(...) -> bool:
    """...Returns True if upsert succeeded, False otherwise."""
    ...
    except Exception as e:
        log(f"Error collecting {table_name}: {e}")
        return False
    ...
    if df.empty:
        log(f"No data for {table_name}; skipping upsert.")
        return True  # Empty data is not an error
    ...
    except Exception as e:
        log(f"Error upserting to {table_name}: {e}")
        return False
```

### Impact
- Callers can now check return value and decide whether to continue or fail
- Backward-compatible: existing callers that ignore return value still work
- Enables better error handling in collection scripts

---

## M2: Centralize Duplicated Utilities

### Problem
5+ duplicated patterns across scripts:

| Utility | Files | Lines |
|---------|-------|-------|
| `NpEncoder` | `generate_live_predictions.py:37-49`, `generate_predictions.py:50-62` | ~26 |
| `_parse_timestamp` | `validate_prediction_tables.py:21-28`, `validate_accuracy_tables.py:24-30`, `check_supported_model_freshness.py:64-71` | ~21 |
| `_write_github_output` | `run_billy_collection.py:67-74`, `run_um_collection.py:109-116`, `run_wsp_collection.py:78-101`, `run_backtest.py:60-65`, `check_supported_model_freshness.py:313-320` | ~65 |
| `batched_values` | `common.py:79-90`, `diagnose_band_data.py:43-45`, `admin/repair_wsp_setlists_range.py:31-39` | ~18 |
| `_write_json_atomic` | `model_readiness.py:43-47`, `recover_deal_last50_local.py:44-48` | ~10 |

### Fix
Move all to `scripts/common.py` and update imports.

### Changes

#### 1. Add to `scripts/common.py`:

```python
import json
import numpy as np

class NpEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy/pandas types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def parse_timestamp(value: str | None) -> date | None:
    """Parse an ISO-like timestamp string to a date."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def write_github_output(key: str, value: str) -> None:
    """Write a key=value pair to GITHUB_OUTPUT for GitHub Actions."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def write_json_atomic(path: str, data: Any) -> None:
    """Write JSON atomically via temp file + rename."""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, cls=NpEncoder)
    os.replace(tmp_path, path)
```

#### 2. Update imports in each file:

| File | Old Import | New Import |
|------|------------|------------|
| `generate_live_predictions.py` | local `NpEncoder` | `from scripts.common import NpEncoder` |
| `generate_predictions.py` | local `NpEncoder` | `from scripts.common import NpEncoder` |
| `validate_prediction_tables.py` | local `_parse_timestamp` | `from scripts.common import parse_timestamp` |
| `validate_accuracy_tables.py` | local `_parse_timestamp` | `from scripts.common import parse_timestamp` |
| `check_supported_model_freshness.py` | local `_parse_timestamp`, `_write_github_output` | `from scripts.common import parse_timestamp, write_github_output` |
| `run_billy_collection.py` | local `_write_github_output` | `from scripts.common import write_github_output` |
| `run_um_collection.py` | local `_write_github_output` | `from scripts.common import write_github_output` |
| `run_wsp_collection.py` | local `_write_github_output` | `from scripts.common import write_github_output` |
| `run_backtest.py` | local `_write_github_output` | `from scripts.common import write_github_output` |
| `diagnose_band_data.py` | local `_batched` | `from scripts.common import batched_values` |
| `admin/repair_wsp_setlists_range.py` | local `_chunked` | `from scripts.common import batched_values` |
| `model_readiness.py` | local `_write_json_atomic` | `from scripts.common import write_json_atomic` |
| `recover_deal_last50_local.py` | local `_write_json_atomic` | `from scripts.common import write_json_atomic` |

### Impact
- Eliminates ~140 lines of duplicated code
- Single source of truth for common utilities
- Easier to maintain and test

---

## M3: Website Quick Wins

### M3.1: Extract Shared SVG Icons

**Problem:** `ChevronIcon`, `CheckIcon`, `ModelAgreeIcon` duplicated in `song-board.tsx` and `deal-mobile-row.tsx`.

**Fix:** Create `apps/web/src/components/icons.tsx`:

```tsx
export function ChevronIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export function CheckIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

export function ModelAgreeIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
```

**Update imports:**
- `song-board.tsx`: Replace local definitions with `import { ChevronIcon, CheckIcon, ModelAgreeIcon } from "./icons"`
- `deal-mobile-row.tsx`: Same

### M3.2: Remove Duplicate `formatPercent`

**Problem:** `formatPercent` defined in both `format.ts:86-88` and `accuracy-table.tsx:16-18`.

**Fix:** In `accuracy-table.tsx`, replace local definition with:
```tsx
import { formatPercent } from "@/lib/format";
```

### M3.3: Extract Band Selection Boilerplate

**Problem:** Every page duplicates the band selection pattern:
```tsx
const bandsResult = await getBands();
const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
const bandSelection = resolveBandSelection(bands, params.band);
if (bandsResult.status === "ready" && bandSelection.isInvalid) {
  return <DataState ... />;
}
```

**Fix:** Create `apps/web/src/lib/data/bands.ts` helper:

```tsx
export async function getBandSelection(
  paramsBand: string | undefined,
): Promise<RouteState<{ selection: BandSelection; bands: BandEntry[] }>> {
  const bandsResult = await getBands();
  if (bandsResult.status !== "ready") {
    return bandsResult as RouteState<{ selection: BandSelection; bands: BandEntry[] }>;
  }
  const selection = resolveBandSelection(bandsResult.bands, paramsBand);
  if (selection.isInvalid) {
    return { status: "empty" };
  }
  return { status: "ready", selection, bands: bandsResult.bands };
}
```

**Update pages:** Replace the 4-line pattern with a single call to `getBandSelection(params.band)`.

### Impact
- Reduces component duplication
- Cleaner imports
- Less boilerplate in page files

---

## M4: Archive Retired CK+ Model

### Problem
CK+ is retired (`lifecycle_stage="retired"`, `enabled_for_pipeline=False`) but still importable and has config exports.

### Fix

#### 1. Move model code to archived directory:
```bash
mkdir -p src/jambandnerd/models/archived/ckplus
mv src/jambandnerd/models/ckplus/* src/jambandnerd/models/archived/ckplus/
rmdir src/jambandnerd/models/ckplus
```

#### 2. Update `src/jambandnerd/models/archived/ckplus/__init__.py`:
```python
"""Archived CK+ model — retained for historical reference only."""
```

#### 3. Remove from registry in `src/jambandnerd/models/registry.py`:
Remove the CK+ `ModelDefinition` entry from `MODEL_DEFINITIONS`.

#### 4. Remove config exports in `src/jambandnerd/config/models.py`:
Remove `CKPLUS_ALPHA_DEFAULT` and any CK+ specific config.

#### 5. Update tests:
- Move `tests/models/test_ckplus.py` to `tests/models/archived/test_ckplus.py` or remove
- Update any test imports

### Impact
- Cleaner codebase
- No risk: model already disabled in pipeline and website

---

## M5: Fix Global Mutable State Caches

### Problem
Three caches never invalidate:
1. `config/bands.py:39-40` — `_cached_registry_band_rows`, `_cached_runtime_band_id_columns`
2. `db/operations.py:15` — `_schema_cache`
3. `data_collection/browser.py:34-35` — `_rate_limit_delay`, `_last_request_time`

### Fix

#### 5.1: Add TTL to band caches in `config/bands.py`:

```python
from datetime import datetime, timedelta

_BAND_CACHE_TTL = timedelta(hours=1)
_cached_registry_band_rows: list[dict] | None = None
_cached_registry_band_rows_at: datetime | None = None

def get_registry_active_band_rows() -> list[dict]:
    global _cached_registry_band_rows, _cached_registry_band_rows_at
    now = datetime.now()
    if (
        _cached_registry_band_rows is not None
        and _cached_registry_band_rows_at is not None
        and now - _cached_registry_band_rows_at < _BAND_CACHE_TTL
    ):
        return _cached_registry_band_rows

    # ... fetch from Supabase ...
    _cached_registry_band_rows = result
    _cached_registry_band_rows_at = now
    return result
```

Same pattern for `_cached_runtime_band_id_columns`.

#### 5.2: Add TTL to schema cache in `db/operations.py`:

```python
_SCHEMA_CACHE_TTL = timedelta(hours=2)
_schema_cache: dict[str, tuple[list[dict], datetime]] = {}

def get_table_schema(table_name: str, client=None) -> list[dict]:
    global _schema_cache
    now = datetime.now()
    if table_name in _schema_cache:
        schema, cached_at = _schema_cache[table_name]
        if now - cached_at < _SCHEMA_CACHE_TTL:
            return schema

    # ... fetch schema ...
    _schema_cache[table_name] = (schema, now)
    return schema
```

#### 5.3: Add refresh mechanism for browser.py rate limiter:

The rate limiter globals are less critical (they're per-process), but add a reset function:

```python
def reset_rate_limiter() -> None:
    """Reset rate limiter state (useful for testing)."""
    global _last_request_time
    _last_request_time = None
```

### Impact
- Prevents stale data from persisting indefinitely
- Low risk: TTL values are conservative (1-2 hours)

---

## M6: Remove force-dynamic from Static Pages

### Problem
`about`, `contact`, `data-use` pages are purely static but have `export const dynamic = "force-dynamic"`.

### Fix
Remove the line from each file:

| File | Line | Action |
|------|------|--------|
| `apps/web/src/app/about/page.tsx` | ~3 | Remove `export const dynamic = "force-dynamic"` |
| `apps/web/src/app/contact/page.tsx` | ~3 | Remove `export const dynamic = "force-dynamic"` |
| `apps/web/src/app/data-use/page.tsx` | ~3 | Remove `export const dynamic = "force-dynamic"` |

### Impact
- Pages will be statically prerendered
- Faster response times
- Zero risk

---

## M7: Centralize Hardcoded Email

### Problem
`CONTACT_EMAIL = "jambandnerd2026@gmail.com"` duplicated in `contact/page.tsx:12` and `data-use/page.tsx:13`.

### Fix

#### 1. Add to `apps/web/src/lib/site.ts`:
```tsx
export const CONTACT_EMAIL = "jambandnerd2026@gmail.com";
```

#### 2. Update imports:
- `apps/web/src/app/contact/page.tsx`: Replace local const with `import { CONTACT_EMAIL } from "@/lib/site"`
- `apps/web/src/app/data-use/page.tsx`: Same

### Impact
- Single source of truth for contact email
- Easy to update in one place

---

## Verification Plan

After all changes:

```bash
# Python verification
npm run verify:python

# Website verification
npm run verify:web

# Full verification
npm run verify:all
```

Expected results:
- All tests pass (407+ from Phase 1-3)
- Website builds successfully
- No linting errors

---

## Session Log Update

Add to `session_logs/2026-05-06/02_performance_review_phases_4-5.md` with:
- All changes made
- Files modified
- Verification results
- Lessons learned
