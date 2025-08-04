# WSP Pipeline Caching Mechanism

## Overview

The Widespread Panic (WSP) data collection pipeline implements an intelligent caching system to optimize
performance and reduce unnecessary API calls. This document explains the caching strategy, implementation
details, and benefits.

## Caching Strategy

The WSP pipeline uses a timestamp-based caching mechanism with the following components:

1. **Show Data Caching**: Tracks when show data was last scraped
2. **Song Data Caching**: Tracks when song catalog was last scraped
3. **Setlist Filtering**: Uses date-based filtering to focus on recent shows

## Implementation Details

### Cache Files

The caching system uses JSON files to store timestamps:

- `shows_cache.json`: Tracks the last time show data was scraped
- `songs_cache.json`: Tracks the last time song data was scraped

### Key Functions

#### Cache Checking

```python
def should_scrape_shows(force_scrape: bool = False, max_age_days: int = 7) -> bool:
    """
    Determines if shows should be scraped based on cache age.
    
    Args:
        force_scrape: If True, ignores cache and returns True
        max_age_days: Maximum age of cache in days (default: 7)
        
    Returns:
        True if shows should be scraped, False otherwise
    """
    if force_scrape:
        return True
    last_scraped = get_last_scrape_timestamp(SHOWS_CACHE_FILE)
    if last_scraped is None:
        return True
    age = datetime.now() - last_scraped
    return age.days >= max_age_days
```

#### Date Filtering

```python
def get_date_filter_cutoff(months_back: int = 3) -> datetime:
    """
    Returns a date cutoff for filtering shows to check for setlists.
    
    Args:
        months_back: Number of months to look back (default: 3)
        
    Returns:
        Datetime object representing the cutoff date
    """
    today = datetime.now()
    return today - timedelta(days=30 * months_back)
```

### Pipeline Entry Points

The WSP pipeline has two main entry points:

1. **`run_pipeline.py`**: Original implementation with caching logic
2. **`run_pipeline_supabase.py`**: Optimized implementation for CI/CD that leverages the caching logic

Both entry points now use the same caching mechanism to avoid unnecessary scraping.

## Optimization Benefits

The caching mechanism provides several key benefits:

1. **Reduced API Load**: Minimizes requests to external APIs
2. **Faster CI/CD Runs**: Daily pipeline runs complete in seconds instead of minutes
3. **Focused Updates**: Only checks recent shows for new setlists
4. **Efficient Resource Usage**: Avoids re-downloading unchanged data

## Execution Patterns

### Update Mode (Default)

In update mode (`update=True`), the pipeline:

1. Checks if show/song data needs refreshing based on cache age
2. If not, loads existing data from Supabase
3. Filters shows to only those from the last 3 months
4. Scrapes setlists only for those recent shows
5. Updates cache timestamps

### Full Mode

In full mode (`update=False`), the pipeline:

1. Still uses caching for show/song data
2. Processes all shows for setlist checking
3. Uses Supabase to avoid re-scraping known setlists

### Force Mode

When forced (`force_scrape_all=True`), the pipeline:

1. Ignores cache timestamps
2. Scrapes all show and song data
3. Processes setlists according to update mode setting

## Monitoring and Maintenance

- **Cache Validity**: Cache files store timestamps to track data freshness
- **Logging**: Detailed logs indicate when caching is used vs. when scraping occurs
- **Performance Metrics**: Pipeline execution time is logged for monitoring

## Future Improvements

Potential enhancements to the caching system:

1. **Differential Updates**: Track individual show changes instead of bulk timestamps
2. **Content-Based Caching**: Hash content to detect actual changes rather than using time-based expiration
3. **Distributed Cache**: Move cache to database for multi-server execution
