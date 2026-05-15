# Technical Overview

This page is retained as a compact historical snapshot. For current operating
guidance, use:

- [Data Strategy](data_strategy.md) for the canonical data contract
- [Architecture Overview](../../contributor/developer_guide/architecture.md) for the current system walkthrough
- [Website Delivery Strategy](../../operations/website_delivery.md) for the live product surface

## Historical Note

The current maintained product surface is the website in `apps/web`. This page
remains only as legacy background and should not be treated as the source of
truth for current model rollout, CI schedules, or product delivery.

## Current Reality At A Glance

- raw data is stored in source-faithful Supabase tables
- normalization and feature generation are shared and in-memory
- each active band has one registered website-facing model version
- CK+ is retired and kept only for historical reference
- live next-show predictions are stored separately from completed-show history
- model metrics come from the retained last-100 completed-show corpus in
  `setlist_results` and `setlist_accuracy`

## Read Next

- [Data Strategy](data_strategy.md)
- [Database](database.md)
- [Predictions Schema](predictions_schema.md)
- [Transformations](transformations.md)
- **Configuration**: Centralized configuration management
- **Logging**: Unified logging format across all components

### External Service Integration

- **Email Service**: SMTP configuration for error notifications
- **Monitoring**: Optional integration with monitoring services
- **Analytics**: Usage tracking for interface optimization
- **Backup**: Integration with cloud backup services

---

## 13. Testing Strategy

### Test Coverage Areas

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Database operations, API interactions
- **Data Validation**: Input/output format verification
- **Model Testing**: Prediction accuracy validation

### Test Data Management

- **Sample Data**: Representative test datasets for each band
- **Mock Services**: Mock external APIs for reliable testing
- **Database**: Separate test database instance
- **Cleanup**: Automated test data cleanup procedures

---

## 14. Monitoring & Observability

### Metrics Collection

- **Pipeline Metrics**: Execution time, success/failure rates
- **Data Metrics**: Record counts, data freshness, validation failures
- **Model Metrics**: Prediction accuracy, confidence distributions
- **System Metrics**: Database performance, API response times

### Alerting Configuration

- **Error Conditions**: Pipeline failures, data validation failures
- **Performance Issues**: Slow queries, high resource usage
- **Data Quality**: Missing data, accuracy degradation
- **Delivery**: Email notifications with actionable information

### Logging Standards

- **Format**: Structured JSON logging for easy parsing
- **Levels**: INFO for normal operations, ERROR for failures, DEBUG for troubleshooting
- **Retention**: 90-day retention with automatic cleanup
- **Correlation**: Request IDs for tracing across components
