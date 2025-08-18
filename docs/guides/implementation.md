# JamBandNerd v2 Implementation Guide

> Repo alignment notes (2025-08-17):
>
> - Goose-first plan for Phase 2: implement one full pipeline before adding other bands.
> - No local `setup_database.py`; MCP/AI handles environment/database setup.
> - Use `src/jambandnerd/db/` (not `database/`) for database utilities in this repo.

Related specs:

- CLI: `documents/planning/cli_spec.md`
- DB Utilities: `documents/planning/db_utilities_spec.md`
- Goose Pipeline: `documents/planning/goose_pipeline_spec.md`
- Predictions & Accuracy Schema: `documents/planning/predictions_accuracy_schema.md`

## Development Strategy

### Modular Development Approach

This implementation follows a modular, AI-assisted development strategy where each component can be
built and tested independently. Each task is designed to be completed in a single AI session with
clear inputs, outputs, and verification steps. The architecture is designed to be highly extensible,
allowing for the easy addition of new bands and prediction models.

### Development Phases

1. **Foundation** (Weeks 1-2): Project setup, data exploration, database design
2. **Data Pipeline** (Weeks 3-4): Collection, transformation, and storage
3. **Modeling** (Weeks 5-6): Notebook model implementation and accuracy tracking
4. **Interface** (Weeks 7-8): Streamlit web application
5. **Automation** (Week 9): GitHub Actions and deployment

---

## Phase 1: Foundation (Weeks 1-2)

### Task 1.1: Project Structure Setup

**Objective**: Create modular project structure and development environment

**AI Session Input**:

- Current JamBandNerd directory structure (from README)
- Requirements for v2 modular architecture
- Python 3.12 + UV setup requirements

**Implementation Steps**:

1. Create new project directory structure (paths adjusted to this repo's `documents/` and `db/`):

```text
JamBandNerd/
├── docs/
│   ├── data_sources/
│   ├── supabase_schema/
│   └── ai_sessions/
├── src/jambandnerd/
│   ├── __init__.py
│   ├── data_collection/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract base classes
│   │   ├── phish/
│   │   ├── goose/
│   │   └── wsp/
│   ├── transformations/
│   │   ├── __init__.py
│   │   └── standardizer.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── notebook/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── operations.py
│   ├── web/
│   │   ├── __init__.py
│   │   └── app.py
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── config.py
├── scripts/
│   ├── run_pipeline.py
│   └── run_all_pipelines.py
├── .env
├── .cursorrules
├── gemini.md
└── pyproject.toml
```

1. Set up pyproject.toml with dependencies:
   - supabase
   - requests
   - beautifulsoup4
   - pandas
   - streamlit
   - python-dotenv

2. Create base configuration and logging utilities

**Verification**:

- Project installs cleanly with `uv pip install .`
- All imports work correctly
- Basic logging functionality works

**Output**: Complete project structure with working development environment

---

### Task 1.2: Data Source Analysis

**Objective**: Document actual API responses and scraping outputs to design raw data schemas

**AI Session Input**:

- Existing JamBandNerd data collection code
- API documentation for phish.net and elgoose.net
- Sample HTML from everydaycompanion.com

**Implementation Steps**:

1. **Phish.net API Analysis**:
   - Make sample API calls to each endpoint
   - Document JSON response structure
   - Identify all fields and data types
   - Note any nested objects or arrays
   - Reference `documents/data/phish_api_schema.md`

2. **Elgoose.net API Analysis**:
   - Analyze show and setlist endpoints
   - Document response formats
   - Reference `documents/data/goose_api_schema.md`

3. **WSP Scraping Analysis**:
   - Analyze HTML structure of show pages
   - Document parsing requirements
   - Reference `documents/data/wsp_webscrape_schema.md`

**Verification**:

- Successfully retrieve sample data from all sources
- Complete documentation of all fields and formats
- Clear mapping from raw data to required standardized format

**Output**: Complete data source documentation in `documents/data/`

---

### Task 1.3: Supabase Schema Design

**Objective**: Design raw data tables based on actual API/scraping analysis

**AI Session Input**:

- Data source documentation from Task 1.2
- Technical specifications requirements
- Band naming conventions (`{band}_` prefix)

**Implementation Steps**:

1. **Design Raw Tables for Each Band**:
   - Create SQL schemas matching exact API response structure
   - Add metadata fields (created_at, updated_at, source_hash)
   - Design for CSV exportability (no JSON columns)
   - Optimize for incremental updates

2. **Design Prediction Tables**:
   - `{band}_predictions` with confidence scores
   - `{band}_accuracy` with top-10/25/50 metrics
   - Indexes for common query patterns

3. **Create Schema Documentation**:
   - `docs/supabase_schema/phish_tables.md`
   - `docs/supabase_schema/goose_tables.md`
   - `docs/supabase_schema/wsp_tables.md`
   - `docs/supabase_schema/prediction_tables.md`

**Verification**:

- Schemas accommodate all fields from data source analysis
- Tables can be created successfully in Supabase
- Sample data can be inserted and queried

**Output**: Complete database schema documentation and SQL creation scripts

---

### Task 1.4: Supabase Setup

**Objective**: Set up Supabase project and create initial tables

**AI Session Input**:

- Schema documentation from Task 1.3
- Supabase project credentials
- MCP integration requirements for data deletion

**Implementation Steps**:

1. **Supabase Project Configuration**:
   - Create new Supabase project
   - Configure API keys and connection strings
   - Set up environment variables

2. **Database Initialization**:
   - Create all raw data tables
   - Create prediction and accuracy tables
   - Set up indexes and constraints
   - Configure row-level security policies

3. **Connection Testing**:
   - Test database connections from Python
   - Verify CRUD operations work correctly
   - Test bulk insert performance

**Verification**:

- All tables created successfully
- Python can connect and perform operations
- Sample data operations work as expected

**Output**: Configured Supabase database ready for data collection

---

## Phase 2: Data Pipeline (Weeks 3-4)

### Task 2.1: Abstract Base Classes

**Objective**: Implement base interfaces for collectors and models

**AI Session Input**:

- Technical specifications API interfaces
- Modular architecture requirements
- Error handling patterns

**Implementation Steps**:

1. **Create `src/jambandnerd/data_collection/base.py`**:
   - Implement `BandCollector` abstract base class
   - Include API optimization methods (get_existing_show_ids, needs_update)
   - Add error handling and retry logic
   - Implement rate limiting utilities

2. **Create `src/jambandnerd/models/base.py`**:
   - Implement `PredictionModel` abstract base class
   - Include accuracy calculation methods (top-10/25/50)
   - Add model versioning support

3. **Create database utilities**:
   - Connection management in `src/jambandnerd/db/connection.py`
   - CRUD operations in `src/jambandnerd/db/operations.py`
   - Bulk insert optimizations

**Verification**:

- Abstract classes can be imported successfully
- Database utilities connect to Supabase
- Rate limiting works correctly

**Output**: Solid foundation classes for all data collection and modeling

---

### Task 2.2: Phish Data Collector

**Objective**: Implement Phish.net API data collection with optimization

**AI Session Input**:

- `docs/data_sources/phish_api.md` documentation
- Abstract base class from Task 2.1
- API key and rate limiting requirements

**Implementation Steps**:

1. **Create `src/jambandnerd/data_collection/phish/collector.py`**:
   - Implement `PhishCollector` class inheriting from `BandCollector`
   - Implement all abstract methods (collect_shows, collect_setlists, collect_songs)
   - Add incremental update logic (only new/changed shows)
   - Include API key authentication and error handling

2. **Optimize API Usage**:
   - Query existing shows before making API calls
   - Batch requests where possible
   - Implement response caching for development
   - Add comprehensive logging

3. **Create collection script**:
   - `scripts/collect_phish.py` for standalone execution
   - Command-line arguments for date ranges
   - Progress reporting and error summary

**Verification**:

- Successfully collect sample Phish shows without duplicate API calls
- Data is properly stored in Supabase tables
- Incremental updates work correctly (only fetch new shows)
- Error handling works for API failures

**Output**: Complete Phish data collector with optimized API usage

---

### Task 2.3: Goose Data Collector

**Objective**: Implement elgoose.net API data collection

**AI Session Input**:

- `docs/data_sources/goose_api.md` documentation
- Working Phish collector as reference
- Base collector class patterns

**Implementation Steps**:

1. **Create `src/jambandnerd/data_collection/goose/collector.py`**:
   - Implement `GooseCollector` following same patterns as Phish
   - Handle API differences (no authentication, different endpoints)
   - Implement incremental collection logic
   - Add appropriate rate limiting (respectful usage)

2. **Test and validate**:
   - Collect sample data and verify format
   - Test incremental updates
   - Verify data quality and completeness

**Verification**:

- Goose data collection works without errors
- Data matches expected schema format
- No duplicate or redundant API calls

**Output**: Complete Goose data collector

---

### Task 2.4: WSP Data Scraper

**Objective**: Implement web scraping for Widespread Panic data

**AI Session Input**:

- `docs/data_sources/wsp_scraping.md` documentation
- Web scraping best practices
- Rate limiting for respectful scraping

**Implementation Steps**:

1. **Create `src/jambandnerd/data_collection/wsp/scraper.py`**:
   - Implement `WSPCollector` with web scraping logic
   - Use BeautifulSoup for HTML parsing
   - Implement respectful rate limiting (1 request per 2 seconds)
   - Add robust error handling for parsing failures

2. **Optimize scraping strategy**:
   - Parse show listing pages first to get show IDs
   - Only scrape individual shows that don't exist in database
   - Handle different HTML structures gracefully
   - Cache responses during development

**Verification**:

- Successfully scrape sample WSP data
- Parsing handles various HTML formats
- Rate limiting prevents server overload
- Data quality matches other sources

**Output**: Complete WSP data scraper with respectful practices

---

### Task 2.5: Data Transformation Pipeline

**Objective**: Create in-memory standardization pipeline for model input

**AI Session Input**:

- Raw data from all three collectors
- Notebook model requirements (from existing codebase)
- Standardization requirements from technical specs

**Implementation Steps**:

1. **Create `src/jambandnerd/transformations/standardizer.py`**:
   - Implement `DataTransformer` class
   - Create methods to standardize show, setlist, and song data
   - Handle band-specific variations in data format
   - Include data validation and quality checks

2. **Design standardized format**:
   - Common field names across all bands
   - Consistent date/time formatting
   - Standardized song names and venue information
   - Clear setlist structure (sets, songs, positions)

3. **Create validation logic**:
   - Check data completeness
   - Validate date ranges and formats
   - Identify and flag data quality issues
   - Log transformation statistics

**Verification**:

- Raw data from all bands transforms to consistent format
- Validation catches common data issues
- Transformation is reversible for debugging
- Performance is acceptable for large datasets

**Output**: Complete data transformation pipeline ready for modeling

---

## Phase 3: Modeling (Weeks 5-6)

### Task 3.1: Notebook Model Implementation

**Objective**: Implement rotation-based prediction model from existing codebase

**AI Session Input**:

- Existing Notebook model code from JamBandNerd v1
- Standardized data format from Task 2.5
- Technical specifications for 30% top-10 accuracy target

**Implementation Steps**:

1. **Create `src/jambandnerd/models/notebook/model.py`**:
   - Implement `NotebookModel` inheriting from `PredictionModel`
   - Adapt existing rotation logic to new standardized data format
   - Implement training method with historical data
   - Create prediction method returning top-50 songs with confidence scores

2. **Enhance model logic**:
   - Improve context weighting (set position, venue, tour, recent history)
   - Add venue-type considerations
   - Include song gap analysis components
   - Optimize for target accuracy metrics

3. **Add model persistence**:
   - Save/load trained model state
   - Version tracking for model improvements
   - Configuration management for parameters

**Verification**:

- Model trains successfully on historical data
- Predictions achieve >30% top-10 accuracy on validation set
- Model produces consistent results across runs
- Prediction confidence scores are well-calibrated

**Output**: Production-ready Notebook model with target accuracy

---

### Task 3.2: Accuracy Calculation System

**Objective**: Implement comprehensive accuracy tracking and calculation

**AI Session Input**:

- Prediction model output format
- Accuracy table schema (top-10/25/50)
- Historical show data for validation

**Implementation Steps**:

1. **Create `src/jambandnerd/models/accuracy.py`**:
   - Implement accuracy calculation for top-10, top-25, top-50
   - Create methods for show-level and aggregate accuracy
   - Add confidence interval calculations
   - Include accuracy trend analysis

2. **Integrate with database**:
   - Store accuracy metrics in `{band}_accuracy` tables
   - Update accuracy when new show data becomes available
   - Create historical accuracy tracking
   - Add accuracy comparison utilities

3. **Create validation framework**:
   - Cross-validation utilities for model testing
   - Historical backtest capabilities
   - Statistical significance testing for accuracy improvements

**Verification**:

- Accuracy calculations match manual verification
- Historical accuracy trends show reasonable patterns
- Database storage and retrieval works correctly
- Statistical tests provide meaningful confidence metrics

**Output**: Complete accuracy tracking system with statistical validation

---

### Task 3.3: Prediction Generation Pipeline

**Objective**: Create automated pipeline to generate and store predictions

**AI Session Input**:

- Trained Notebook model from Task 3.1
- Accuracy system from Task 3.2
- Database operations for prediction storage

**Implementation Steps**:

1. **Create `src/jambandnerd/models/predictor.py`**:
   - Implement prediction pipeline orchestration
   - Load latest model and generate predictions for recent shows
   - Calculate and update accuracy metrics
   - Store predictions with confidence scores and metadata

2. **Add prediction utilities**:
   - Methods to predict for specific shows or date ranges
   - Batch prediction processing for efficiency
   - Prediction validation and quality checks
   - Model performance monitoring

3. **Create prediction scripts**:
   - `scripts/generate_predictions.py` for standalone execution
   - Support for single band or all bands
   - Command-line options for date ranges and model versions

**Verification**:

- Predictions generate successfully for all bands
- Accuracy metrics update correctly after new predictions
- Performance is acceptable for large prediction batches
- Error handling prevents partial prediction states

**Output**: Complete prediction generation pipeline ready for automation

---

## Phase 4: Interface (Weeks 7-8)

### Task 4.1: Streamlit Application Structure

**Objective**: Create basic Streamlit application with band/model selection

**AI Session Input**:

- Technical specifications for web interface
- Supabase prediction and accuracy data
- Streamlit best practices for performance

**Implementation Steps**:

1. **Create `src/jambandnerd/web/app.py`**:
   - Basic Streamlit application structure
   - Sidebar for band selection (Phish, Goose, WSP)
   - Model selection dropdown (Notebook, with placeholder for CK+)
   - Main content area for predictions display

2. **Add database connectivity**:
   - Supabase connection with caching for performance
   - Query utilities for predictions and accuracy data
   - Error handling for database connectivity issues

3. **Create basic layouts**:
   - Prediction display with confidence scores
   - Historical accuracy charts
   - Model performance comparison tables

**Verification**:

- Streamlit app launches without errors
- Band and model selection works correctly
- Database queries execute and display data
- Interface is responsive on different screen sizes

**Output**: Functional Streamlit application with basic features

---

### Task 4.2: Prediction Display Interface

**Objective**: Create compelling visualization for song predictions

**AI Session Input**:

- Prediction data format from database
- User interface requirements for confidence display
- Streamlit visualization components

**Implementation Steps**:

1. **Create prediction display components**:
   - Top-10 predictions with confidence bars
   - Expandable top-25 and top-50 predictions
   - Color-coded confidence levels
   - Song information (last played, frequency, etc.)

2. **Add interactive features**:
   - Filter predictions by confidence threshold
   - Show/hide different prediction tiers
   - Sort by confidence, alphabetical, or last played
   - Search functionality for specific songs

3. **Enhance visualization**:
   - Progress bars for confidence scores
   - Icons or indicators for prediction rank
   - Responsive design for mobile viewing
   - Clear labeling and explanations

**Verification**:

- Predictions display clearly and attractively
- Interactive features work smoothly
- Interface provides good user experience
- Performance is acceptable with large prediction sets

**Output**: Professional prediction display interface

---

### Task 4.3: Accuracy Dashboard

**Objective**: Create historical accuracy visualization and model comparison

**AI Session Input**:

- Accuracy data from database
- Model comparison requirements
- Streamlit charting capabilities

**Implementation Steps**:

1. **Create accuracy visualization**:
   - Line charts for accuracy trends over time
   - Bar charts comparing top-10/25/50 accuracy
   - Model performance comparison charts
   - Statistical significance indicators

2. **Add interactive features**:
   - Date range selection for accuracy analysis
   - Band-specific accuracy deep dives
   - Model version comparison
   - Accuracy metric explanations and interpretations

3. **Create summary statistics**:
   - Overall accuracy summary cards
   - Best/worst performance periods
   - Accuracy improvement trends
   - Model confidence calibration charts

**Verification**:

- Accuracy charts display correctly and update with new data
- Interactive features provide meaningful insights
- Performance statistics are accurate and informative
- Interface helps users understand model performance

**Output**: Complete accuracy dashboard with historical analysis

---

### Task 4.4: Application Polish and Deployment Prep

**Objective**: Finalize Streamlit application and prepare for deployment

**AI Session Input**:

- Complete Streamlit application from previous tasks
- Deployment requirements (Streamlit Cloud or Railway)
- Performance optimization needs

**Implementation Steps**:

1. **Application optimization**:
   - Implement caching for database queries
   - Optimize page load times
   - Add loading indicators for slow operations
   - Error handling and user-friendly error messages

2. **User experience improvements**:
   - Add help text and explanations for model concepts
   - Include information about data sources and update frequency
   - Create about page with project information
   - Add feedback mechanism or contact information

3. **Deployment preparation**:
   - Environment variable configuration
   - Requirements.txt or equivalent for deployment platform
   - Error logging and monitoring setup
   - Performance testing with production data volumes

**Verification**:

- Application performs well with full dataset
- All features work correctly in production-like environment
- Error handling prevents application crashes
- User experience is smooth and intuitive

**Output**: Production-ready Streamlit application

---

## Phase 5: Automation (Week 9)

### Task 5.1: Pipeline Orchestration Script

**Objective**: Create unified pipeline execution script for all components

**AI Session Input**:

- All implemented collectors, transformers, and models
- Modular execution requirements
- Error handling and email notification needs

**Implementation Steps**:

1. **Create `scripts/run_pipeline.py`**:
   - Command-line interface for pipeline execution
   - Options for running all bands or specific bands
   - Options for running specific pipeline stages (collect, transform, predict)
   - Comprehensive logging and progress reporting

2. **Add orchestration logic**:
   - Execute data collection for all bands in parallel where possible
   - Run transformation pipeline on collected data
   - Generate predictions using latest models
   - Update accuracy metrics with new predictions

3. **Implement error handling**:
   - Continue pipeline execution when individual components fail
   - Collect and summarize all errors for reporting
   - Send email notifications for critical failures
   - Create detailed execution reports

**Verification**:

- Pipeline executes successfully end-to-end
- Individual component failures don't stop entire pipeline
- Error reporting provides actionable information
- Execution completes within reasonable time frame

**Output**: Complete pipeline orchestration system

---

### Task 5.2: Email Notification System

**Objective**: Implement email alerts for pipeline failures and monitoring

**AI Session Input**:

- Pipeline execution results and error patterns
- Email service options (to be determined)
- Notification requirements for different error types

**Implementation Steps**:

1. **Research and select email service**:
   - Compare options: SendGrid, AWS SES, Gmail SMTP, etc.
   - Consider cost, reliability, and ease of setup
   - Choose based on personal preference and requirements

2. **Create `src/jambandnerd/utils/notifications.py`**:
   - Email sending utilities with error handling
   - Template system for different notification types
   - Rate limiting to prevent notification spam
   - Configuration for email settings

3. **Integrate with pipeline**:
   - Send notifications for API failures and persistent errors
   - Include error summaries and suggested actions
   - Provide pipeline execution status reports
   - Add success notifications for major milestones

**Verification**:

- Email notifications send successfully
- Error reports contain actionable information
- Notification system doesn't interfere with pipeline execution
- Email formatting is clear and professional

**Output**: Complete email notification system

---

### Task 5.3: GitHub Actions Automation

**Objective**: Set up automated daily pipeline execution

**AI Session Input**:

- Complete pipeline orchestration script
- GitHub Actions workflow requirements
- Security considerations for API keys and database credentials

**Implementation Steps**:

1. **Create `.github/workflows/daily-pipeline.yml`**:
   - Scheduled execution (daily at appropriate time)
   - Manual trigger option for testing
   - Environment variable configuration
   - Timeout and resource management

2. **Set up secure credential management**:
   - Configure GitHub repository secrets
   - Environment variables for API keys and database connection
   - Secure handling of sensitive information
   - Rotation plan for credentials

3. **Add workflow optimization**:
   - Parallel execution where possible
   - Appropriate resource allocation
   - Artifact saving for debugging
   - Status reporting and notification integration

**Verification**:

- Workflow executes successfully on schedule
- All credentials and environment variables work correctly
- Pipeline completes within GitHub Actions time limits
- Error handling and notifications work in automated environment

**Output**: Fully automated daily pipeline execution

---

### Task 5.4: Deployment and Monitoring Setup

**Objective**: Deploy Streamlit application and set up monitoring

**AI Session Input**:

- Completed Streamlit application
- Deployment platform choice (Streamlit Cloud or Railway)
- Monitoring requirements for production system

**Implementation Steps**:

1. **Deploy Streamlit application**:
   - Set up deployment platform account
   - Configure environment variables and database connections
   - Deploy application and verify functionality
   - Set up custom domain if desired

2. **Configure monitoring**:
   - Set up application monitoring and alerting
   - Database performance monitoring
   - Pipeline execution monitoring
   - User analytics (optional)

3. **Create maintenance procedures**:
   - Backup and recovery procedures
   - Deployment rollback plan
   - Database maintenance and cleanup procedures
   - Performance optimization guidelines

**Verification**:

- Application is accessible and functional in production
- Monitoring provides meaningful insights
- All automated processes work correctly
- System is maintainable and reliable

**Output**: Fully deployed and monitored production system

---

## AI Session Management

### Session Start Template

```markdown
# JamBandNerd v2 Development Session

## Context
- **Project**: JamBandNerd v2 - Cloud-native jam band setlist prediction platform
- **Current Task**: [Task number and name from implementation guide]
- **Previous Progress**: [Brief summary of completed tasks]

## Current Task Objective
[Copy objective from implementation guide]

## Required Inputs
[List all inputs specified in task - code files, documentation, credentials, etc.]

## Expected Outputs
[List expected outputs and verification criteria]

## Key Constraints
- Python 3.12 + UV package manager
- Supabase for database (minimize API calls)
- Modular architecture for independent components
- 30% top-10 accuracy target for models
- API rate limiting and respectful usage

## Success Criteria
[Copy verification criteria from task]

Ready to begin implementation.
```

### Session End Template

```markdown
# Task Completion Summary

## Task Completed
[Task number and name]

## Outputs Created
- [ ] [List all files/components created]
- [ ] [Include verification results]
- [ ] [Document any deviations from plan]

## Next Task
[Reference to next task in implementation guide]

## Notes for Next Session
- [Any important context or decisions made]
- [Issues encountered and how they were resolved]
- [Recommendations for next task]

## Files to Commit
[List all files that should be committed to repository]

Session completed successfully.
```

---

## Component Testing Strategy

### Individual Component Testing

Each task should include verification steps that can be run independently:

1. **Data Collectors**: Test with small date ranges, verify data format
2. **Transformers**: Test with sample data, verify output format
3. **Models**: Test with historical data, verify accuracy calculations
4. **Database Operations**: Test CRUD operations, verify performance
5. **Web Interface**: Test with sample data, verify responsiveness

### Integration Testing

After completing related tasks, test component integration:

1. **End-to-end data flow**: Raw collection → transformation → modeling → storage
2. **Web interface integration**: Database queries → visualization → user interaction
3. **Pipeline orchestration**: Full pipeline execution with error scenarios

### Performance Testing

Validate system performance at key milestones:

1. **Database performance**: Query response times with full dataset
2. **Model training time**: Acceptable training duration with historical data
3. **Prediction generation**: Batch prediction performance
4. **Web interface responsiveness**: Page load times and user interaction speed

---

## Risk Mitigation

### Technical Risks

- **API Changes**: Maintain flexible parsing, implement fallback strategies
- **Model Accuracy**: Start with proven Notebook model, validate against historical data
- **Performance Issues**: Implement caching, optimize database queries, profile bottlenecks

### Operational Risks

- **Data Source Failures**: Implement graceful degradation, continue with existing data
- **Database Issues**: Implement retry logic, maintain local backups during development
- **Deployment Problems**: Test in staging environment, maintain rollback procedures

### Development Risks

- **Scope Creep**: Stick to MVP features, document future enhancements separately
- **Time Overruns**: Focus on core functionality, polish in later iterations
- **Integration Issues**: Test component interfaces early, maintain clear contracts

This implementation guide provides a clear roadmap for building JamBandNerd v2 with AI assistance,
emphasizing modularity, testability, and incremental progress toward a production-ready system.
