# Technical Overview

This page is the compact reference view of the system. For the canonical data
contract, use the [Data Strategy](data_strategy.md). For the contributor-facing
system walkthrough, use the
[Architecture Overview](../../contributor/developer_guide/architecture.md).

## Product Direction

JamBandNerd is a Python 3.12 data platform for jam band setlist collection,
transformation, prediction, and website delivery. The public surface is the
website; Streamlit remains in the repo for internal legacy/debugging use only
and is no longer part of the active public product path.

## Current Technical Shape

- **Ingestion**: band-specific collectors write source-faithful rows into raw
  Supabase tables.
- **Normalization**: shared code aligns source-specific raw schemas onto one
  internal contract for prediction.
- **Transforms**: feature generation is centralized and in-memory.
- **Models**: Notebook and CK+ consume the same `ModelData` object.
- **Storage**: predictions and accuracy are stored in unified model-based
  tables.
- **Delivery**: the website reads from Supabase-backed prediction and accuracy
  data.

## Canonical Flow

```text
collect raw data
  -> normalize shows/setlists/songs
  -> sort shows deterministically
  -> apply reference_date cutoff
  -> build ModelData
  -> generate predictions
  -> backtest and save accuracy
```

## Important Invariants

- Shared transforms and models are band-agnostic.
- `reference_date` is mandatory for feature generation and backtesting.
- Historical sequence is ordered by `show_date` and a stable tiebreaker.
- No intermediate transformed Supabase tables are allowed.
- Aggregate accuracy tables are derived from `accuracy_per_show`, not vice
  versa.

## Where To Read Next

- [Data Strategy](data_strategy.md)
- [Database](database.md)
- [Predictions Schema](predictions_schema.md)
- [Transformations](transformations.md)

### External API Integrations

#### Phish.net API

- **Base URL**: `https://api.phish.net/v5/`
- **Authentication**: API key in header
- **Rate Limit**: 1000 requests/day
- **Key Endpoints**:
  - `/shows/query` - Show search and listing
  - `/shows/{show_id}` - Detailed show information
  - `/setlists/{show_id}` - Complete setlist data

#### Elgoose.net API

- **Base URL**: `https://elgoose.net/api/`
- **Authentication**: None required
- **Rate Limit**: Respectful usage (no published limits)
- **Key Endpoints**:
  - `/shows` - Show listing with date filters
  - `/shows/{show_id}/setlist` - Setlist details

#### Everydaycompanion.com Scraping

- **Method**: Web scraping with BeautifulSoup
- **Rate Limit**: 1 request per 2 seconds
- **Parsing Strategy**: HTML table parsing for show/setlist data
- **Error Handling**: Retry with exponential backoff

---

## 8. Model Specifications

### Notebook Model (MVP)

#### Notebook Model Algorithm

- **Type**: Rotation-based statistical model
- **Input**: Historical setlists with song position and context
- **Logic**: Analyze song appearance patterns in similar contexts
- **Output**: Probability distribution over next song candidates

#### Implementation Details

```python
class NotebookModel(PredictionModel):
    def __init__(self):
        self.rotation_patterns = {}
        self.context_weights = {
            'set_position': 0.3,
            'venue_type': 0.2,
            'tour_context': 0.2,
            'recent_history': 0.3
        }

    def predict(self, current_setlist, context):
        # Calculate rotation-based probabilities
        # Weight by contextual factors
        # Return top 10 predictions with confidence scores
        pass
```

#### Target Accuracy

- **Primary Goal**: >30% top-1 accuracy
- **Secondary Goals**: >50% top-3, >70% top-5 accuracy
- **Baseline Comparison**: Random selection ~3% accuracy

### CK+ Model (Phase 2)

#### CK+ Model Algorithm

- **Type**: Gap-based statistical model
- **Input**: Song gap analysis (shows since last played)
- **Logic**: Statistical likelihood based on historical gap patterns
- **Integration**: Pluggable alongside Notebook model

---

## 9. Infrastructure Specifications

### Deployment Architecture

#### Supabase Production Configuration

- **Plan**: Pro tier for production workloads
- **Features**: Real-time subscriptions, edge functions, auth (future)
- **Backup**: Automated daily backups with 7-day retention
- **Security**: Row-level security policies, API key rotation

#### GitHub Actions Pipeline

```yaml
# Daily pipeline execution
name: Daily Data Pipeline
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM daily
  workflow_dispatch:  # Manual trigger

jobs:
  collect:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        band: [phish, goose, wsp]
    steps:
      - name: Collect data
        run: python scripts/collect.py --band ${{ matrix.band }}

  predict:
    needs: collect
    runs-on: ubuntu-latest
    steps:
      - name: Generate predictions
        run: python scripts/predict.py --all

  notify:
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Send error notification
        run: python scripts/notify.py --error
```

#### Website Deployment

- **Platform**: Vercel is the target production host for the website app
- **Configuration**: Environment variables for Supabase connection and frontend runtime config
- **Scaling**: Managed hosting with preview deploys and production rollouts
- **Monitoring**: Platform logging plus application-level health checks

### Development Environment

#### Local Setup

- **Python**: 3.12 with UV package manager
- **Database**: Local Supabase instance for development
- **Testing**: Pytest for unit tests, data validation tests
- **Code Quality**: Black formatting, Ruff linting

#### CI/CD Pipeline

- **Testing**: Automated test execution on pull requests
- **Linting**: Code quality checks with ruff and black
- **Security**: Dependency vulnerability scanning
- **Deployment**: Automatic website preview and production deployment on branch updates

---

## 10. Performance Specifications

### Response Time Requirements

- **Data Collection**: Complete within 60 minutes for all bands
- **Prediction Generation**: Complete within 30 minutes per band
- **Website**: Page loads under 3 seconds
- **Database Queries**: Sub-second response for prediction retrieval

### Scalability Considerations

- **Database**: Designed for 10,000+ shows per band
- **Predictions**: Support 1,000+ predictions per show
- **Models**: Pluggable architecture for easy model addition
- **Data Volume**: Efficient storage with cleanup policies

### Resource Management

- **Memory**: Transformation processing in memory (no temp tables)
- **CPU**: Parallel processing where possible (band-level parallelism)
- **Storage**: Optimized indexes, data retention policies
- **Network**: Request batching, respectful API usage

---

## 11. Security Specifications

### Authentication & Authorization

- **API Keys**: Secure environment variable storage
- **Database**: Connection string encryption, credential rotation
- **GitHub**: Repository secrets for sensitive configuration
- **Email**: Service account for notification delivery

### Data Protection

- **Input Validation**: Sanitize all external data inputs
- **SQL Injection**: Parameterized queries, ORM usage
- **Rate Limiting**: Respect external API limits, implement internal limits
- **Error Handling**: No sensitive data in error messages

### Monitoring & Alerting

- **Failed Requests**: Monitor API response codes, retry logic
- **Data Quality**: Validate data completeness and accuracy
- **System Health**: Pipeline execution monitoring
- **Security Events**: Log authentication failures, unusual access patterns

---

## 12. Integration Specifications

### Modular Component Integration

- **Data Flow**: Clear interfaces between collection, transformation, modeling
- **Error Propagation**: Graceful degradation, continue pipeline on component failure
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
