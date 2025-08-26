# Pipeline Optimization Guide

This guide covers the performance optimizations implemented for the JamBandNerd data pipeline, focusing on GitHub Actions reliability and execution efficiency.

## Overview

The JamBandNerd pipeline has been optimized to reduce execution time from 15-20 minutes to 3-7 minutes while improving reliability and error handling. Two execution strategies are available:

1. **Optimized Single-Script Pipeline** (3-4 minutes) - Recommended for development and testing
2. **Parallel Matrix Pipeline** (5-7 minutes) - Default for production GitHub Actions

## Optimized Pipeline Script

### Usage

```bash
# Run complete pipeline for all bands (fastest)
python scripts/run_optimized_pipeline.py --band all

# Run single band pipeline
python scripts/run_optimized_pipeline.py --band goose
python scripts/run_optimized_pipeline.py --band phish

# Skip accuracy calculations for faster execution
python scripts/run_optimized_pipeline.py --band all --skip-accuracy
```

### Key Features

- **Data Reuse**: Loads raw data once per band and reuses it across both prediction models
- **Minimal Database Calls**: Eliminates redundant Supabase fetches
- **Comprehensive Timing**: Reports execution time for each pipeline stage
- **Graceful Error Handling**: Continues execution when individual components fail
- **Progress Tracking**: Timestamped logging with clear stage indicators

### Performance Comparison

| Execution Method | Total Time | Data Fetches | Error Recovery |
|-----------------|------------|--------------|----------------|
| **Original Sequential** | 15-20 min | 8x redundant | ❌ Fail-stop |
| **Parallel Matrix** | 5-7 min | 8x parallel | ✅ Partial success |
| **Optimized Script** | 3-4 min | 2x reused | ✅ Graceful handling |

## GitHub Actions Optimization

### Parallel Execution Strategy

The default GitHub Actions workflow uses a matrix strategy to run pipeline components in parallel:

```yaml
# Data collection runs in parallel for both bands
collect-data:
  strategy:
    matrix:
      band: [goose, phish]

# Predictions run in parallel for all band/model combinations  
generate-predictions:
  strategy:
    matrix:
      band: [goose, phish]
      model: [notebook, ckplus]

# Accuracy calculations run in parallel
calculate-accuracy:
  strategy:
    matrix:
      band: [goose, phish]  
      model: [notebook, ckplus]
```

### Manual Control Options

The workflow supports manual triggers with options:

- **Band Selection**: Run pipeline for specific bands only (goose/phish/all)
- **Optimized Pipeline**: Toggle experimental single-script execution
- **Error Recovery**: Individual job failures don't stop the entire pipeline

### Reliability Enhancements

- **Timeout Management**: Appropriate timeouts for each pipeline stage
- **Fail-Fast Disabled**: One band failure doesn't stop the other
- **Partial Success Tracking**: Pipeline can complete with some component failures
- **Enhanced Logging**: Collapsible groups and progress indicators

## Performance Optimizations

### Debug Mode Control

Production runs use `debug=False` to eliminate verbose logging:

```python
# Optimized for production
model_data = generate_model_data(shows_df, setlists_df, reference_date, debug=False)
```

### Model Robustness Improvements

**CK+ Model Enhancements:**
- Parameter validation on initialization
- Finite value checks for mathematical operations
- Z-score clamping to prevent extreme outliers
- Comprehensive error handling with graceful fallbacks

**Transformation Optimizations:**
- Conditional debug output reduces log noise
- Efficient data type conversions
- Memory-optimized DataFrame operations

### Database Efficiency

- **Chunked Fetching**: Robust pagination with proper error handling
- **Conflict Resolution**: Proper upsert columns for data consistency
- **Connection Pooling**: Singleton Supabase client reduces overhead
- **Schema Validation**: Skip validation in production for speed

## Monitoring & Observability

### GitHub Actions Features

- **Workflow Summaries**: Emoji status indicators and detailed results
- **Matrix Visibility**: Clear band/model combination tracking  
- **Timing Metrics**: Execution time reporting for optimization insights
- **Error Categorization**: Distinguishes between critical and non-critical failures

### Local Development Monitoring

```bash
# Example optimized pipeline output
[18:32:15] 🚀 Starting JamBandNerd Optimized Pipeline
[18:32:16] Starting optimized pipeline for GOOSE
[18:32:16] Step 1: Collecting goose data...
[18:32:45] ✅ Data collection completed in 28.9s
[18:32:45] Step 2: Loading and preparing goose data for predictions...
[18:32:48] ✅ Data preparation completed in 2.3s
[18:32:48] Step 3: Generating predictions for both models...
[18:32:52] ✅ Notebook predictions saved (50 songs)
[18:32:55] ✅ CK+ predictions saved (50 songs)
[18:32:55] Prediction timing: Notebook=3.8s, CK+=2.7s
[18:32:55] Step 4: Calculating accuracy metrics...
[18:33:15] ✅ Notebook accuracy calculated
[18:33:18] ✅ CK+ accuracy calculated
[18:33:18] 🎉 GOOSE pipeline completed in 62.4s total
```

## Best Practices

### Development Usage

```bash
# Fast iteration during model development
python scripts/run_optimized_pipeline.py --band goose --skip-accuracy

# Complete validation before production
python scripts/run_optimized_pipeline.py --band all
```

### Production Deployment

- Use **parallel matrix pipeline** as default for reliability
- Enable **optimized pipeline** for experimental faster execution
- Monitor **GitHub Actions summaries** for performance trends
- Set up **alerts** for persistent pipeline failures

### Error Recovery

The optimized pipeline provides detailed success/failure reporting:

```bash
📊 Pipeline Summary (Total: 125.3s)
  GOOSE: ✅ SUCCESS (62.4s) - Collection, Notebook, CK+, NB-Acc, CK+-Acc
  PHISH: ❌ FAILED (58.2s) - API timeout during collection
```

## Troubleshooting

### Common Issues

**GitHub Actions Timeout:**
- Check individual job timeouts (currently 45-60 minutes)
- Consider using optimized pipeline for faster execution
- Monitor Supabase connection health

**Partial Failures:**
- Review individual matrix job logs
- Validate API keys and Supabase credentials
- Check for data quality issues in source APIs

**Performance Degradation:**
- Monitor database response times
- Check for API rate limiting
- Validate transformation efficiency with debug mode

### Performance Monitoring

Track these metrics over time:
- Total pipeline execution time
- Individual stage timing (collection, prediction, accuracy)
- Error rates by band and model
- GitHub Actions runner resource usage

## Future Enhancements

### Potential Optimizations

- **Caching Strategy**: Implement Redis caching for frequently accessed data
- **Incremental Updates**: Only process new/changed data since last run
- **Database Optimization**: Implement read replicas for accuracy calculations
- **Parallel Accuracy**: Run accuracy calculations concurrently with predictions

### Monitoring Improvements

- **Performance Dashboard**: Real-time pipeline metrics visualization
- **Alerting System**: Proactive notifications for performance degradation
- **Cost Monitoring**: Track GitHub Actions runner costs and optimize usage
- **Data Quality Metrics**: Monitor prediction accuracy trends over time
