# Streamlit App Output Schema

This document defines the standardized output format for prediction data displayed in the
JamBandNerd Streamlit web application.

## Overview

The Streamlit app displays prediction data from two models (CK+ and Notebook) for multiple bands
(Phish, Goose, WSP). Each prediction list is limited to 50 items and sorted according to
model-specific criteria.

## Data Sources

- **Source Tables**: `predictions_ckplus` and `predictions_notebook` in Supabase
- **Filtering**: Data is filtered by band and limited to the most recent prediction date
- **Sorting**: Applied according to model-specific criteria (see below)
- **Limit**: Maximum 50 items per prediction list

## CK+ Model Output Schema

**Display Name**: "CK+"

**Sorting Criteria**: `ckplus_score` descending (highest scores first)

**Columns Displayed**:

| Display Name | Source Column | Data Type | Description |
|--------------|---------------|-----------|-------------|
| Song | `song_name` | TEXT | Name of the song |
| Times Played Overall | `times_played_total` | INTEGER | Total times the song has been played historically |
| LTP Date | `last_played_date` | TEXT | Last time played date (MM/DD/YYYY format) |
| Current Gap | `current_gap` | INTEGER | Number of shows since the song was last played |
| Avg Gap | `avg_gap` | FLOAT | Historical average gap between performances |
| Gap Ratio | `gap_ratio` | FLOAT | Ratio of current gap to average gap |
| Gap Z-Score | `gap_z_score` | FLOAT | Z-score of the current gap relative to historical distribution |
| CK+ Score | `ckplus_score` | FLOAT | Final calculated score from the CK+ model (higher = more likely) |

## Notebook Model Output Schema

**Display Name**: Band-specific (e.g., "Trey's Notebook", "Rick's Notebook", "JoJo's Notebook")

**Sorting Criteria**:

1. `times_played_last_year` descending (primary)
2. `current_gap` descending (secondary)

**Columns Displayed**:

| Display Name | Source Column | Data Type | Description |
|--------------|---------------|-----------|-------------|
| Song | `song_name` | TEXT | Name of the song |
| Times Played Last Year | `times_played_last_year` | INTEGER | Number of times played in the last 365 days |
| LTP Date | `last_played_date` | TEXT | Last time played date (MM/DD/YYYY format) |
| Current Gap | `current_gap` | INTEGER | Number of shows since the song was last played |
| Average Gap | `avg_gap` | FLOAT | Historical average gap between performances |
| Median Gap | `median_gap` | FLOAT | Historical median gap between performances |

## Data Processing Notes

### Ranking System

- Each displayed table includes a "Rank" column (1-50) based on the sorting criteria
- Ranking is applied after filtering and sorting but before display

### Error Handling

- If no data is found for a band/model combination, a warning message is displayed
- If database connection fails, an error message is shown with details
- Empty datasets result in "No data to display" message

### Data Freshness

- Data is cached for 1 hour in the Streamlit app for performance
- Predictions are typically updated daily via automated pipelines
- The most recent `prediction_date` for each band is automatically selected

## Band-Specific Configurations

### Supported Bands

- **Phish**: Uses "Trey's Notebook" label for Notebook model
- **Goose**: Uses "Rick's Notebook" label for Notebook model
- **WSP**: Uses "JoJo's Notebook" label for Notebook model

### Model Availability

- All supported bands have both CK+ and Notebook models available
- UM (Umphrey's McGee) is temporarily disabled but schema supports future addition

## Technical Implementation

### Data Flow

1. User selects band and model type in Streamlit sidebar
2. App queries unified Supabase tables (`predictions_ckplus` or `predictions_notebook`)
3. Data is filtered by band and sorted according to model criteria
4. Results are limited to top 50 and formatted for display
5. Column names are mapped from database schema to user-friendly display names

### Performance Considerations

- Database queries use pagination for large datasets
- Results are cached in Streamlit for 1 hour
- Only necessary columns are selected and processed
- Sorting is performed at the application level after data retrieval

## Future Enhancements

### Potential Additions

- Date range filtering for historical predictions
- Confidence intervals or prediction probability scores
- Song popularity metrics and trend analysis
- Export functionality for prediction lists
- Real-time updates without caching delays

### Schema Evolution

- New bands can be added by updating the `BAND_DISPLAY_NAMES` and `NOTEBOOK_LABELS` constants
- Additional model types can be supported by extending the column configuration logic
- New prediction features can be added to the display schema as models evolve
