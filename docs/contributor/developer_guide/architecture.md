# Architecture Overview

This document defines JamBandNerd’s technical foundation. Update as architecture or standards evolve.

## 1. Overview

**Project Goal:**
A modular platform for collecting, processing, and predicting jam band setlists, with robust orchestration, analytics, and a website-first product surface. The design is extensible to add new bands and models.

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
- **Components**: Band-specific collectors with unified interface. The design allows for easy addition of new bands by implementing new collector modules.
- **Output**: Raw data tables in Supabase (`{band}_*_raw`)
- **WSP Collector**: The collector for Widespread Panic (`everydaycompanion.com`) is a special case. To bypass sophisticated bot detection and IP blocking (especially in a CI/CD environment like GitHub Actions), the collector uses a browser automation strategy:
  - **In CI/CD**: It uses **Playwright** with a headless **Firefox** browser to simulate a real user, executing JavaScript and handling complex site interactions.
  - **Locally**: It defaults to the standard `requests` library for efficiency.
  - This dual approach ensures both robust data collection in automated environments and fast, simple execution for local development.

#### Transformation Layer

- **Purpose**: Convert raw data to a standardized format for modeling
- **Processing**: Reads from raw tables and transforms data in-memory before feeding to models.
- **Output**: In-memory `ModelData` objects; no intermediate tables are written.

#### Model Layer

- **Purpose**: Generate predictions using standardized data
- **Models**: Pluggable architecture supporting multiple algorithms (Notebook, CK+).
- **Output**: Predictions stored in Supabase with confidence scores.

#### Presentation Layer

- **Purpose**: User interface for prediction exploration
- **Framework**: Website-first architecture, with a monorepo frontend app as the target public surface.
- **Current State**: The existing Streamlit app in `src/jambandnerd/web/` remains available as a legacy transition surface until website cutover.
- **Data**: Server-side reads from Supabase are the preferred target architecture for the website.

#### Orchestration Layer

- **Purpose**: Coordinate pipeline execution and automation
- **Scheduling**: GitHub Actions for daily pipeline execution.
- **Monitoring**: Error detection and logging.
