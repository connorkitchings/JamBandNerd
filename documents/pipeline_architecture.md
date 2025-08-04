# JamBandNerd Pipeline Architecture

## Overview

The JamBandNerd project consists of two main pipeline types:

1. **Data Collection Pipelines**: Responsible for scraping and storing band data
2. **Prediction Pipelines**: Generate song predictions based on collected data

This document outlines the architecture, optimization strategies, and execution patterns for these pipelines.

## Data Collection Architecture

### Supported Bands

The system currently supports data collection for:

- Phish
- Goose
- Widespread Panic (WSP)
- Umphrey's McGee (UM) - *Note: Currently out of scope due to missing data collection directory*

### Pipeline Components

Each band's data collection pipeline follows a similar pattern:

1. **API/Web Scraping**: Band-specific modules for retrieving raw data
2. **Data Transformation**: Converting raw data to standardized formats
3. **Data Storage**: Saving to both local CSV files and Supabase database
4. **Caching Mechanisms**: Optimizing scraping frequency based on data freshness

### Caching Strategy

To optimize performance and reduce unnecessary API calls, the pipelines implement intelligent caching:

- **Show Data**: Only re-scraped if cache is older than 7 days or forced
- **Song Data**: Only re-scraped if cache is older than 7 days or forced
- **Setlist Data**:
  - In update mode: Only checks recent shows (last 3 months)
  - In full mode: Checks all shows but uses database to avoid re-scraping known setlists

### Entry Points

Each band has dedicated entry points:

- `jambandnerd.data_collection.[band].run_pipeline`: Main entry point with caching logic
- `scripts/run_all_pipelines.py`: Orchestration script for parallel execution of all bands

## Prediction Architecture

The prediction system follows a clean separation of concerns:

1. **Band-Agnostic Models** (`models/`): Core prediction algorithms
   - CK+ Model: Gap-based prediction algorithm
   - Notebook Model: Frequency-based prediction algorithm

2. **Band-Specific Pipelines** (`predictions/`):
   - Data transformation from band-specific formats to model inputs
   - Model execution using band-agnostic algorithms
   - Saving predictions to band-specific tables

### Prediction Tables

All bands use consistent table naming conventions:

- `[band]_predictions_ckplus`: For CK+ model predictions
- `[band]_predictions_notebook`: For notebook model predictions

## CI/CD Integration

The system uses GitHub Actions for automated daily pipeline execution:

- **Workflow**: `.github/workflows/daily-pipeline.yml`
- **Schedule**: Runs daily at 20:00 UTC (3 PM Eastern)
- **Execution Pattern**: 
  1. Data collection for all bands runs in parallel using `scripts/run_all_pipelines.py`
  2. Prediction pipelines run after data collection completes
  3. Logs are captured as artifacts for monitoring

## Optimization Strategies

The following optimizations have been implemented:

1. **Parallel Execution**: All band pipelines run concurrently for faster completion
2. **Intelligent Caching**: Avoids unnecessary scraping based on data freshness
3. **Date-Based Filtering**: Only processes recent shows in update mode
4. **Chunked Database Operations**: Prevents API timeouts for large datasets
5. **Retry Logic**: Handles transient failures with exponential backoff

## Monitoring and Maintenance

- **Logs**: All pipeline runs generate detailed logs in the `logs/` directory
- **GitHub Actions Artifacts**: Workflow runs capture logs for 7 days
- **Status Reporting**: Pipeline completion status is reported in GitHub Actions summary
