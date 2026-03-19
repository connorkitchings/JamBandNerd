# JamBandNerd v2 Technical Specifications

This living document defines JamBandNerd’s technical foundation. Update as architecture or standards
evolve.

## 1. Overview

**Project Goal:**
A modular platform for collecting, processing, and predicting jam band setlists, with robust
orchestration, analytics, and a website-first product surface. The design is extensible to add new
bands and models.

**Repository:**
`https://github.com/connorkitchings/JamBandNerd`

## 2. Architecture

### Data Flow Diagram

```mermaid
graph TD
    subgraph " "
        direction LR
        A[External APIs &<br>Websites]
    end

    subgraph "GitHub Actions: Daily Pipeline"
        B(run_optimized_pipeline.py)
    end
    
    subgraph "Supabase Database"
        C[fa:fa-database Raw Data<br><i>{band}_*_raw</i>]
        D[fa:fa-database Prediction & Accuracy<br><i>predictions_*, accuracy_*</i>]
    end

    subgraph "In-Memory Processing"
        E[pandas DataFrames]
        F(ModelData Object)
        G[Notebook & CK+<br>Predictors]
    end
    
    subgraph "Presentation"
        H[fa:fa-desktop Website<br><i>target</i>]
    end

    A --> B
    B -- "1. Collect" --> C
    C -- "2. Load" --> E
    E -- "3. Transform (gaps.py)" --> F
    F -- "4. Predict" --> G
    G -- "5. Save" --> D
    D -- "6. Display" --> H
```

### Component Architecture

#### Data Collection Layer

- **Purpose**: Ingest raw data from external sources
- **Components**: Band-specific collectors with unified interface. The design allows for easy
  addition of new bands by implementing new collector modules.
- **Output**: Raw data tables in Supabase (`{band}_*_raw`)
- **Error Handling**: Continue pipeline with existing data on source failure

#### Transformation Layer

- **Purpose**: Convert raw data to a standardized format for modeling
- **Processing**: Reads from raw tables and transforms data in-memory before feeding to models.
- **Output**: In-memory DataFrames or objects; no intermediate tables are written.
- **Validation**: Data quality checks and cleansing

#### Model Layer

- **Purpose**: Generate predictions using standardized data
- **Models**: Pluggable architecture supporting multiple algorithms. New models can be easily
  integrated by adhering to the common model interface.
- **Output**: Predictions stored in Supabase with confidence scores
- **Accuracy**: Real-time accuracy calculation and historical tracking

#### Presentation Layer

- **Purpose**: User interface for prediction exploration
- **Framework**: Website-first architecture, with a monorepo frontend app as the target public surface
- **Features**: Band/model selection, prediction display, historical explorer, and accuracy trends
- **Data**: Server-side Supabase reads are the preferred target architecture for the website
- **Current State**: The existing Streamlit app remains available as a legacy transition surface

#### Orchestration Layer

- **Purpose**: Coordinate pipeline execution and automation
- **Scheduling**: GitHub Actions for daily pipeline execution
- **Monitoring**: Error detection and email notification
- **Modularity**: Independent component execution capabilities

---

## 3. Standards & Practices

- Python code uses type hints and docstrings
- Formatting: black; Linting: ruff; Testing: pytest
- Modular design with band-specific collectors and common interfaces

## 4. Session Workflow

1) Review `docs/overview/project/prd.md`, `docs/overview/project/schedule.md`, latest dev log
2) Execute the smallest valuable task end-to-end within a session
3) Update dev log and docs for handoff

## 5. Phase 2 Direction (Goose-first)

- Implement base abstractions
- Build a single, full working pipeline for Goose (collect → transform → predict)
- Add additional bands after Goose pipeline is verified

---

## 6. Database Design

### Supabase Schema

#### Raw Data Tables (Band-Specific)

**Show Tables**: `{band}_shows`

```sql
CREATE TABLE phish_shows (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(50) UNIQUE NOT NULL,
    show_date DATE NOT NULL,
    venue_name VARCHAR(255),
    venue_city VARCHAR(100),
    venue_state VARCHAR(50),
    venue_country VARCHAR(50),
    tour_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Setlist Tables**: `{band}_setlists`

```sql
CREATE TABLE phish_setlists (
    id SERIAL PRIMARY KEY,
    show_id VARCHAR(50) NOT NULL,
    set_number INTEGER NOT NULL,
    song_position INTEGER NOT NULL,
    song_name VARCHAR(255) NOT NULL,
    song_length INTEGER, -- seconds
    encore BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (show_id) REFERENCES phish_shows(show_id)
);
```

**Song Tables**: `{band}_songs`

```sql
CREATE TABLE phish_songs (
    id SERIAL PRIMARY KEY,
    song_name VARCHAR(255) UNIQUE NOT NULL,
    first_played DATE,
    last_played DATE,
    times_played INTEGER DEFAULT 0,
    average_length INTEGER, -- seconds
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Prediction and Accuracy Tables (Unified by Model)

Prediction and accuracy tables are unified by model slug (e.g., `predictions_notebook`, `accuracy_ckplus`). For the canonical `CREATE TABLE` statements for these tables, please see the [Unified Table Schemas](../schemas/unified_tables.md) document, which is the single source of truth.

### Data Cleanup Policies

#### Retention Rules

- **Raw Data**: Keep all historical data (reference for model improvements)
- **Predictions**: Keep predictions for last 2 years, archive older data quarterly
- **Accuracy Tracking**: Keep all accuracy records (small table, valuable for trends)
- **Logs**: Retain for 90 days, purge automatically

#### Optimization

- **Indexing**: Optimize for common queries (show_id, model_name, date ranges)
- **Partitioning**: Consider date-based partitioning for large prediction tables
- **Archival**: Move old predictions to separate archive tables

---

## 7. API Specifications

### Internal API Design

#### Data Collection Interface

```python
class BandCollector(ABC):
    """Abstract base class for band data collectors"""

    @abstractmethod
    def collect_shows(self, start_date: date, end_date: date) -> List[Dict]:
        """Collect show data for date range"""
        pass

    @abstractmethod
    def collect_setlists(self, show_ids: List[str]) -> List[Dict]:
        """Collect setlist data for specific shows"""
        pass

    @abstractmethod
    def collect_songs(self) -> List[Dict]:
        """Collect comprehensive song catalog"""
        pass
```

#### Transformation Interface

```python
class DataTransformer:
    """Standardize raw data for model consumption"""

    def transform_for_model(self,
                           raw_data: Dict,
                           model_type: str) -> StandardizedData:
        """Transform raw data to model-specific format"""
        pass

    def validate_data(self, data: StandardizedData) -> ValidationResult:
        """Validate data quality and completeness"""
        pass
```

#### Model Interface

```python
class PredictionModel(ABC):
    """Abstract base class for prediction models"""

    @abstractmethod
    def train(self, data: StandardizedData) -> None:
        """Train model with historical data"""
        pass

    @abstractmethod
    def predict(self,
                current_setlist: List[str],
                context: Dict) -> List[Prediction]:
        """Generate next song predictions"""
        pass

    @abstractmethod
    def calculate_accuracy(self,
                          predictions: List[Prediction],
                          actual_songs: List[str]) -> AccuracyMetrics:
        """Calculate prediction accuracy"""
        pass
```

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
