# Troubleshooting Data Quality Issues

This guide provides systematic approaches for diagnosing and resolving data collection and prediction quality issues in the JamBandNerd platform.

## Common Symptoms

### Stale Predictions
- **Symptom**: Songs that were recently played appear in top predictions
- **Root Cause**: Missing or outdated setlist data
- **Impact**: Predictions don't reflect recent shows, reducing accuracy

### Missing Setlist Data
- **Symptom**: Shows exist in database but have no associated setlist entries
- **Root Cause**: API collection failures, database constraint errors
- **Impact**: Incomplete historical data for model training

## Diagnostic Workflow

### Step 1: Identify the Issue
```bash
# Check recent predictions for a band
uv run python -c "
import json
from src.jambandnerd.db.connection import get_supabase_client
client = get_supabase_client()
result = client.table('predictions_notebook').select('*').eq('band', 'BAND_NAME').order('predicted_at', desc=True).limit(1).execute()
if result.data:
    predictions = json.loads(result.data[0]['predictions'])
    print('Top 5 predictions:')
    for i, p in enumerate(predictions[:5], 1):
        print(f'{i}. {p[\"song_name\"]} (last: {p.get(\"last_played_date\", \"unknown\")})')
"
```

### Step 2: Verify Recent Show Data
```bash
# Check for recent shows and their setlists
uv run python -c "
from datetime import date, timedelta
from src.jambandnerd.db.connection import get_supabase_client
client = get_supabase_client()

# Check recent shows
recent_date = str(date.today() - timedelta(days=1))
shows = client.table('BAND_shows_raw').select('*').eq('show_date', recent_date).execute()
if shows.data:
    for show in shows.data:
        show_id = show['api_show_id']
        venue = show.get('venue_name', 'Unknown')
        print(f'Show: {recent_date} - {venue} (ID: {show_id})')
        
        # Check setlist
        setlist = client.table('BAND_setlists_raw').select('song_name').eq('api_show_id', show_id).execute()
        if setlist.data:
            songs = [s['song_name'] for s in setlist.data]
            print(f'  Setlist: {len(songs)} songs')
            print(f'  Sample: {songs[:5]}')
        else:
            print('  ⚠️ No setlist found - DATA COLLECTION ISSUE')
else:
    print('No shows found for recent date')
"
```

### Step 3: Check API Data Availability  
```bash
# Test direct API call for missing setlist
uv run python -c "
from src.jambandnerd.data_collection.BAND.collector import BANDCollector
collector = BANDCollector()
show_id = 'SHOW_ID_HERE'
setlist_data = collector._fetch_BAND_endpoint(f'setlists/showid/{show_id}')
if setlist_data:
    print(f'API has setlist data: {len(setlist_data)} items')
    songs = [item.get('song', 'Unknown') for item in setlist_data[:10]]
    print(f'Sample songs: {songs}')
else:
    print('API has no setlist data')
"
```

### Step 4: Diagnose Collection Failures
Common issues and solutions:

#### Database Constraint Errors
```
Error: null value in column "created_at" violates not-null constraint
```
**Solution**: Run collection with validation bypassed:
```bash
uv run python scripts/run_BAND_collection.py --only-setlists --skip-validation
```

#### API Rate Limiting
```  
Rate limit reached (80/80), sleeping for 54.5s
```
**Solution**: Normal behavior - collection will resume automatically

#### Schema Validation Failures
```
Validation failed for BAND_setlists_raw: TypeMismatch
```
**Solution**: Review and fix data types, or skip validation temporarily

## Resolution Steps

### Fix Missing Setlist Data
1. **Re-run Collection**:
   ```bash
   uv run python scripts/run_BAND_collection.py --only-setlists
   ```

2. **Skip Validation if Needed**:
   ```bash  
   uv run python scripts/run_BAND_collection.py --only-setlists --skip-validation
   ```

3. **Verify Data Updated**:
   ```bash
   # Check that recent shows now have setlists
   # Re-run Step 2 diagnostic above
   ```

### Regenerate Predictions
1. **Update Notebook Model**:
   ```bash
   uv run python scripts/generate_predictions.py --band BAND --model notebook
   ```

2. **Update CK+ Model**:
   ```bash
   uv run python scripts/generate_predictions.py --band BAND --model ckplus
   ```

3. **Verify Predictions Updated**:
   ```bash
   # Re-run Step 1 diagnostic to confirm predictions are current
   ```

## Prevention

### Data Freshness Monitoring
- Monitor the gap between latest show dates and latest setlist dates
- Set up alerts for setlist collection failures
- Regular verification that recently played songs are properly excluded from predictions

### Collection Health Checks
- Monitor collection run logs for database constraint errors
- Verify API connectivity and rate limit compliance
- Track collection success rates per band

### Validation Flexibility
- Consider making database constraints more lenient for operational data
- Implement graceful handling of validation failures
- Maintain backup collection methods for critical data

## Example: Phish Data Quality Issue (2025-09-13)

**Problem**: "Chalk Dust Torture" ranked #1 in predictions despite being played previous night.

**Root Cause**: Database constraint error prevented setlist insertion for 2025-09-12 show.

**Solution Applied**:
```bash
# 1. Confirmed API had correct data
# 2. Re-ran collection with validation skipped  
uv run python scripts/run_phish_collection.py --only-setlists --skip-validation
# 3. Regenerated predictions
uv run python scripts/generate_predictions.py --band phish --model notebook
# 4. Verified CDT no longer in top predictions
```

**Outcome**: Predictions updated correctly, CDT excluded from top 50.

---

For additional support, check the dev logs in `docs/logs/` for similar issues and their resolutions.