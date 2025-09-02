# WSP Data Collection Improvements

This document outlines planned improvements for the Widespread Panic (WSP) data collector.

## Current Status

The WSP collector is **production-ready** with the following features:

- ✅ Complete historical show collection (1986-2025)
- ✅ Enhanced setlist parsing with Set 0 (soundcheck) support
- ✅ Performance optimized (year filtering, optimized queries)
- ✅ URL redirect handling
- ✅ Data contamination prevention with comprehensive validation
- ✅ Progress tracking and error handling

## Planned Improvements

### 1. Show Notes Extraction (Priority: Medium)

**Goal**: Extract and parse show notes from setlist pages to capture special events and context.

**Examples from everydaycompanion.com**:

- `[Soundcheck; Panic en la Playa Once]` → Parse as show type and event
- `[Panic en la Playa Doce; 'Folsom Prison Blues' rap by JB during 'Let It Rock']` → Extract event and song-specific notes

**Implementation Strategy**:

```python
def _extract_show_notes(self, soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract bracketed notes and special event information."""
    # Look for bracketed content like [Soundcheck; Event Name]
    # Parse special event names (Panic en la Playa, festivals)
    # Extract performance notes and special details
    # Return structured show metadata
```

**Database Impact**: Add `show_notes` and `event_type` columns to `wsp_shows_raw` table.

### 2. Enhanced Venue Data Parsing (Priority: Medium)

**Goal**: Improve venue name normalization and extract additional venue metadata.

**Current Issues**:

- Venue names may have inconsistent formatting
- Missing capacity, type, or geographical data that could be extracted

**Implementation Strategy**:

```python
def _parse_venue_details(self, venue_cell) -> Dict[str, Any]:
    """Extract comprehensive venue information."""
    # Normalize venue names (remove extra spaces, standardize formats)
    # Extract venue type (theater, amphitheater, festival grounds, etc.)
    # Parse full address information when available
    # Add venue capacity if displayed on pages
```

**Database Impact**: Consider adding `venue_type`, `venue_capacity`, `full_address` columns.

### 3. Enhanced Error Handling (Priority: Medium)

**Goal**: Improve robustness and error recovery for edge cases.

**Areas for Improvement**:

#### A. Retry Logic for Failed Parses

```python
def _scrape_with_retry(self, show_url: str, max_attempts: int = 3):
    """Implement exponential backoff retry for failed requests."""
    # Retry with different parsing strategies
    # Handle temporary network issues
    # Log detailed failure information for debugging
```

#### B. Fallback Parsing Methods

```python
def _fallback_parsing_strategies(self, soup: BeautifulSoup):
    """Multiple parsing approaches for difficult pages."""
    # Strategy 1: Text-based parsing (current primary)
    # Strategy 2: Table-based parsing (current fallback)  
    # Strategy 3: Pattern matching for specific edge cases
    # Strategy 4: Manual pattern detection for known problematic shows
```

#### C. Data Quality Monitoring

```python
def _validate_setlist_structure(self, setlist_data: List[Dict]):
    """Validate parsed setlist makes structural sense."""
    # Check for reasonable number of songs per set
    # Validate set numbering sequence (1, 2, E)
    # Flag shows with suspicious patterns for manual review
    # Generate data quality reports
```

#### D. Progressive Parsing

```python  
def _progressive_collection(self, shows: List[Dict]):
    """Collect data with graceful degradation on failures."""
    # Continue processing other shows if one fails
    # Collect partial data when complete parsing fails
    # Queue failed shows for retry later
    # Generate collection success/failure reports
```

## Implementation Priority

1. **High Priority**: Already completed
   - ✅ Performance optimizations
   - ✅ Data contamination prevention
   - ✅ URL redirect handling

2. **Medium Priority**: Future development
   - Show notes extraction
   - Enhanced venue parsing  
   - Improved error handling

3. **Low Priority**: Nice to have
   - Advanced venue geocoding
   - Historical data correction tools
   - Real-time collection monitoring

## Testing Strategy

When implementing these improvements:

1. **Test with Known Edge Cases**: Use problematic shows identified during development
2. **Validate Data Quality**: Ensure no regression in current parsing quality
3. **Performance Testing**: Maintain current collection speed
4. **Incremental Rollout**: Test new features on limited date ranges first

## Notes

- The current collector handles 99%+ of shows correctly
- Focus on incremental improvements rather than major rewrites
- Maintain backward compatibility with existing data schemas
- Document any new edge cases discovered during development
