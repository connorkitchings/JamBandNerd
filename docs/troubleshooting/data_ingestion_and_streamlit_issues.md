# Data Ingestion and Streamlit Last Setlist Issues

**Date**: 2025-10-04  
**Status**: Identified Issues  
**Priority**: HIGH

## Executive Summary

This document analyzes issues with data ingestion for all bands (Goose, Phish, WSP, Billy) and the "Last Show Setlist" feature in the Streamlit web app. The analysis identifies root causes and provides specific fixes.

---

## 🔴 **Critical Issues Identified**

### **Issue 1: Band-Specific ID Column Inconsistencies**

**Problem**: The `fetch_last_show_setlist()` function in Streamlit doesn't properly handle different ID column names across bands.

**Root Cause**:
```python
# Lines 213-218 in app.py
if band == "phish":
    id_col = "api_show_id"
    pos_col = "position"
else:
    id_col = "show_id"
    pos_col = "song_position"
```

**Issue**: Goose data has been showing problems because:
1. The Goose shows table uses `show_id` (correct)
2. But the Goose setlists table might have been populated with `api_show_id` in some cases
3. This causes mismatches when trying to find setlists for recent shows

**Evidence from Workflow** (lines 247-252):
```python
# GitHub Actions tries to dynamically determine column name
id_col = 'api_show_id' if band == 'phish' else 'show_id'
setlist_ids = set(setlists[id_col].astype(str)) if not setlists.empty else set()
```

---

### **Issue 2: Date Handling Inconsistency**

**Problem**: Multiple date column names are used across tables without consistent normalization.

**Root Cause**: Different tables use different column names:
- Goose raw: `showdate` (from API) → needs normalization to `show_date`
- Phish raw: `show_date` (already normalized)
- WSP raw: `show_date` (already normalized)

**Evidence in Streamlit** (lines 513-518):
```python
if band == "phish":
    show_date_key = "show_date"
elif band == "goose":
    show_date_key = "show_date"  # Assumes normalized, but may not be!
else:  # WSP
    show_date_key = "show_date"
```

---

### **Issue 3: Missing Setlist Data Detection**

**Problem**: The GitHub Actions workflow has sophisticated detection for Phish missing setlists (lines 104-155), but:
1. Only runs for Phish
2. Doesn't run for Goose or WSP
3. Doesn't prevent pipeline from continuing with bad data

**Current Workflow Logic**:
```yaml
- name: Verify Data Freshness
  if: steps.check.outputs.should_run == 'true' && matrix.band == 'phish'
  # ^^^ ONLY RUNS FOR PHISH!
```

---

### **Issue 4: Collection Script ID Normalization**

**Problem**: The collection scripts normalize data differently.

**Goose Collection** (`run_goose_collection.py` lines 76-78):
```python
record = {
    "show_id": str(show_id),  # ✅ Normalizes to show_id
    "show_date": _parse_date(item.get("showdate")),  # ✅ Normalizes to show_date
```

**But Goose Setlists** (lines 135-136):
```python
record = {
    "show_id": str(show_id),  # ✅ Correct
```

**Issue**: If the Goose API returns data with `api_show_id` anywhere, and that's not properly mapped, we get mismatches.

---

### **Issue 5: Streamlit Last Show Logic Race Condition**

**Problem**: The Streamlit app tries to find the "last completed show" but the logic has multiple failure points.

**Current Flow** (lines 199-281):
1. Get last 50 shows from `{band}_shows_raw` (by date descending)
2. Get all setlists from `{band}_setlists_raw`
3. Find intersection using `id_col`
4. Pick most recent show from intersection

**Failure Points**:
- **Point A**: If `id_col` is wrong → no intersection found
- **Point B**: If show dates aren't properly sorted → wrong show selected
- **Point C**: If setlists use different ID format → no match

---

## 🎯 **Specific Fixes Required**

### **Fix 1: Standardize ID Column Configuration**

**Create Centralized Config** (already done in `config.py`, but need to use it):

```python
# In config.py (lines 60-65)
BAND_ID_COLUMNS: Final[dict[str, str]] = {
    "goose": "show_id",
    "phish": "api_show_id",
    "wsp": "show_id"
}
```

**Update Streamlit App**:
```python
# Replace hardcoded logic in fetch_last_show_setlist()
from jambandnerd.config import BAND_ID_COLUMNS

id_col = BAND_ID_COLUMNS.get(band, "show_id")
```

**Update GitHub Actions Workflow**:
```python
# In daily-pipeline.yml lines 247-252
from jambandnerd.config import BAND_ID_COLUMNS
id_col = BAND_ID_COLUMNS.get(band, 'show_id')
```

---

### **Fix 2: Enhance Data Freshness Check**

**Extend to All Bands** (not just Phish):

```yaml
- name: Verify Data Freshness
  if: steps.check.outputs.should_run == 'true'  # Remove && matrix.band == 'phish'
  id: data_check
  continue-on-error: true
  run: |
    source .venv/bin/activate
    echo "::group::Verifying data freshness for ${{ matrix.band }}"
    
    python -c "
    import sys, pandas as pd, os
    from datetime import date, timedelta
    sys.path.insert(0, 'src')
    from jambandnerd.db.connection import get_supabase_client
    from jambandnerd.config import BAND_ID_COLUMNS
    
    band = '${{ matrix.band }}'
    client = get_supabase_client()
    id_col = BAND_ID_COLUMNS.get(band, 'show_id')
    
    # Get shows from last 7 days
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    shows = pd.DataFrame(client.table(f'{band}_shows_raw').select('*').gte('show_date', cutoff).execute().data)
    setlists = pd.DataFrame(client.table(f'{band}_setlists_raw').select(id_col).execute().data)
    
    if not shows.empty:
        show_ids = set(shows[id_col].astype(str))
        setlist_ids = set(setlists[id_col].astype(str)) if not setlists.empty else set()
        missing = show_ids - setlist_ids
        
        if missing:
            print(f'::warning::WARNING: {len(missing)} recent shows missing setlist data for {band}')
            for show_id in list(missing)[:5]:
                show = shows[shows[id_col].astype(str) == show_id].iloc[0]
                print(f\"  - {show.get('show_date', 'Unknown date')} (ID: {show_id})\")
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f'missing_data=true\n')
                f.write(f'missing_count={len(missing)}\n')
        else:
            print(f'✅ All recent shows have setlist data for {band}')
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f'missing_data=false\n')
                f.write(f'missing_count=0\n')
    "
    
    echo "::endgroup::"
```

---

### **Fix 3: Add Diagnostic Script**

**Create `scripts/diagnose_band_data.py`**:

```python
#!/usr/bin/env python3
"""Diagnose data consistency issues for a band."""
import argparse
import sys
import os
import pandas as pd
from datetime import date, timedelta

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.config import BAND_ID_COLUMNS

def diagnose_band(band: str) -> dict:
    """Run comprehensive diagnostics on band data."""
    client = get_supabase_client()
    id_col = BAND_ID_COLUMNS.get(band, "show_id")
    
    results = {
        "band": band,
        "id_column": id_col,
        "issues": []
    }
    
    # Check 1: Verify shows table
    print(f"\n{'='*60}")
    print(f"Diagnosing {band.upper()} Data")
    print(f"{'='*60}")
    print(f"Primary ID Column: {id_col}")
    
    shows_table = f"{band}_shows_raw"
    setlists_table = f"{band}_setlists_raw"
    
    # Fetch recent shows
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    shows_resp = client.table(shows_table).select("*").gte("show_date", cutoff).execute()
    shows_df = pd.DataFrame(shows_resp.data)
    
    print(f"\n📊 Shows in last 30 days: {len(shows_df)}")
    
    if shows_df.empty:
        results["issues"].append("No recent shows found")
        return results
    
    # Check for ID column presence
    if id_col not in shows_df.columns:
        results["issues"].append(f"ID column '{id_col}' missing from shows table")
        print(f"❌ Column '{id_col}' NOT FOUND in shows table!")
        print(f"Available columns: {', '.join(shows_df.columns)}")
        return results
    
    print(f"✅ ID column '{id_col}' found in shows table")
    
    # Fetch setlists
    setlists_resp = client.table(setlists_table).select("*").execute()
    setlists_df = pd.DataFrame(setlists_resp.data)
    
    print(f"📋 Total setlist records: {len(setlists_df)}")
    
    if setlists_df.empty:
        results["issues"].append("No setlist data found")
        return results
    
    # Check for ID column in setlists
    if id_col not in setlists_df.columns:
        results["issues"].append(f"ID column '{id_col}' missing from setlists table")
        print(f"❌ Column '{id_col}' NOT FOUND in setlists table!")
        print(f"Available columns: {', '.join(setlists_df.columns)}")
        return results
    
    print(f"✅ ID column '{id_col}' found in setlists table")
    
    # Find orphaned shows (shows without setlists)
    show_ids = set(shows_df[id_col].astype(str))
    setlist_ids = set(setlists_df[id_col].astype(str))
    orphaned = show_ids - setlist_ids
    
    print(f"\n🔍 Orphaned shows (shows without setlists): {len(orphaned)}")
    
    if orphaned:
        results["issues"].append(f"{len(orphaned)} shows without setlist data")
        print("\nFirst 10 orphaned shows:")
        for show_id in list(orphaned)[:10]:
            show = shows_df[shows_df[id_col].astype(str) == show_id].iloc[0]
            print(f"  - {show.get('show_date', 'Unknown')} (ID: {show_id})")
    else:
        print("✅ All recent shows have setlist data")
    
    # Check date column consistency
    date_col = "show_date"
    if date_col not in shows_df.columns:
        results["issues"].append(f"Date column '{date_col}' missing")
        print(f"❌ Date column '{date_col}' NOT FOUND!")
    else:
        print(f"✅ Date column '{date_col}' found")
        # Check for null dates
        null_dates = shows_df[date_col].isna().sum()
        if null_dates > 0:
            results["issues"].append(f"{null_dates} shows with null dates")
            print(f"⚠️  {null_dates} shows have null dates")
    
    print(f"\n{'='*60}")
    if results["issues"]:
        print(f"❌ Found {len(results['issues'])} issue(s)")
        for issue in results["issues"]:
            print(f"  - {issue}")
    else:
        print("✅ No issues found")
    print(f"{'='*60}\n")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose band data issues")
    parser.add_argument("--band", required=True, choices=["goose", "eggy", "phish", "wsp", "billy", "um"])
    args = parser.parse_args()
    
    results = diagnose_band(args.band)
    sys.exit(1 if results["issues"] else 0)
```

---

### **Fix 4: Update Streamlit fetch_last_show_setlist()**

**Current Issues**:
- Hardcoded column names
- No error logging for debugging
- No fallback logic

**Improved Version**:

```python
@st.cache_data(ttl=300)
def fetch_last_show_setlist(
    _db_client: Client, band: str
) -> tuple[pd.DataFrame, dict | None]:
    """Fetch the most recent completed show's setlist for the given band."""
    from jambandnerd.config import BAND_ID_COLUMNS
    
    if band not in BAND_CONFIG:
        return pd.DataFrame(), None
    
    try:
        # Use centralized config for ID columns
        id_col = BAND_ID_COLUMNS.get(band, "show_id")
        pos_col = "position" if band == "phish" else "song_position"
        
        setlist_table = f"{band}_setlists_raw"
        shows_table = f"{band}_shows_raw"
        
        # Get recent shows with explicit date filtering
        today_iso = date.today().isoformat()
        recent_shows_resp = (
            _db_client.table(shows_table)
            .select(f"{id_col}, show_date")
            .lt("show_date", today_iso)
            .order("show_date", desc=True)
            .limit(50)
            .execute()
        )
        
        if not recent_shows_resp.data:
            st.error(f"No recent shows found for {band}")
            return pd.DataFrame(), None
        
        recent_shows = recent_shows_resp.data
        recent_ids = [str(r.get(id_col)) for r in recent_shows if r.get(id_col) is not None]
        
        if not recent_ids:
            st.error(f"No valid show IDs found for {band}")
            return pd.DataFrame(), None
        
        # Get setlists for these shows
        setlist_ids_resp = (
            _db_client.table(setlist_table)
            .select(id_col)
            .in_(id_col, recent_ids)
            .execute()
        )
        
        setlist_ids = {str(r.get(id_col)) for r in (setlist_ids_resp.data or []) if r.get(id_col) is not None}
        
        if not setlist_ids:
            st.warning(f"No setlists found for recent {band} shows. Recent shows may not have been played yet.")
            return pd.DataFrame(), None
        
        # Find most recent show with setlist
        candidates = [r for r in recent_shows if str(r.get(id_col)) in setlist_ids]
        
        if not candidates:
            st.warning(f"Could not match shows with setlists for {band}")
            return pd.DataFrame(), None
        
        candidates_sorted = sorted(candidates, key=lambda x: str(x.get("show_date", "")), reverse=True)
        most_recent_show_id = str(candidates_sorted[0].get(id_col))
        most_recent_show_date = candidates_sorted[0].get("show_date")
        
        # Fetch full setlist
        setlist_data = (
            _db_client.table(setlist_table)
            .select(f"set_number, {pos_col}, song_name")
            .eq(id_col, most_recent_show_id)
            .order("set_number")
            .order(pos_col)
            .execute()
        )
        
        setlist_df = pd.DataFrame(setlist_data.data)
        
        # Fetch show details
        show_details = None
        show_query = (
            _db_client.table(shows_table)
            .select("*")
            .eq(id_col, most_recent_show_id)
            .limit(1)
            .execute()
        )
        
        if show_query.data:
            show_details = show_query.data[0]
        
        return setlist_df, show_details
        
    except Exception as e:
        st.error(f"Failed to fetch last show setlist for {band}: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame(), None
```

---

## 🧪 **Testing Protocol**

### **Test 1: Verify ID Columns**

```bash
# For each band, check what ID columns exist
uv run python -c "
import pandas as pd
from src.jambandnerd.db.connection import get_supabase_client

client = get_supabase_client()
for band in ['goose', 'phish', 'wsp']:
    print(f'\n{band.upper()}:')
    shows = pd.DataFrame(client.table(f'{band}_shows_raw').select('*').limit(1).execute().data)
    setlists = pd.DataFrame(client.table(f'{band}_setlists_raw').select('*').limit(1).execute().data)
    print(f'  Shows columns: {list(shows.columns)}')
    print(f'  Setlists columns: {list(setlists.columns)}')
"
```

### **Test 2: Run Diagnostic Script**

```bash
uv run python scripts/diagnose_band_data.py --band goose
uv run python scripts/diagnose_band_data.py --band phish
uv run python scripts/diagnose_band_data.py --band wsp
```

### **Test 3: Verify Streamlit Last Show**

1. Start Streamlit app locally
2. For each band, check if "Last Show Setlist" displays
3. Verify show date, venue, and song list are correct
4. Check browser console for JavaScript errors

---

## 📋 **Action Items**

- [ ] Create `scripts/diagnose_band_data.py`
- [ ] Update Streamlit `fetch_last_show_setlist()` to use `BAND_ID_COLUMNS`
- [ ] Update GitHub Actions workflow to check all bands (not just Phish)
- [ ] Run diagnostic script for all bands
- [ ] Fix any ID column mismatches in database
- [ ] Test Streamlit app for each band
- [ ] Add logging to collection scripts
- [ ] Document band-specific quirks in `docs/reference/`

---

## 🔗 **Related Files**

- `src/jambandnerd/web/app.py` (lines 199-281, 503-647)
- `.github/workflows/daily-pipeline.yml` (lines 68-176)
- `scripts/get_last_completed_show_date.py`
- `scripts/run_goose_collection.py`
- `src/jambandnerd/config.py`
