# JamBandNerd Product Requirements Document

## Executive Summary

JamBandNerd v2 transforms setlist prediction from a local analytics tool into a cloud-native
platform that provides real-time predictions for jam band performances. The platform serves both
casual fans seeking show insights and data enthusiasts exploring predictive modeling accuracy.

### Vision Statement

Create the most accurate and accessible jam band setlist prediction platform, enabling fans to
enhance their concert experience through data-driven insights.

---

## Product Goals

### Primary Goals

1. **Automate Data Pipeline**: Eliminate manual data collection and processing
2. **Provide Real-Time Predictions**: Deliver next-song predictions through a production website
3. **Demonstrate Model Accuracy**: Track and display prediction performance over time
4. **Scale to Multiple Bands**: Support Phish, Goose, and Widespread Panic initially

### Secondary Goals

1. **Enable Model Comparison**: Allow users to compare different prediction approaches
2. **Build Community Engagement**: Create shareable predictions and accuracy tracking
3. **Establish Data Foundation**: Build robust infrastructure for future prediction types

---

## Target Users

### Primary Users

### Jam Band Enthusiasts

- Attend shows regularly and want enhanced experience
- Interested in setlist patterns and song probabilities
- Comfortable with basic data interpretation
- Use mobile devices during shows

### Data Science Hobbyists

- Interested in prediction model performance
- Want to understand methodology and accuracy
- May contribute to model improvement
- Desktop/laptop primary usage

### Secondary Users

### Casual Fans

- Occasional show attendance
- Basic curiosity about upcoming songs
- Simple interface preferred
- Mixed device usage

---

## Core Features

### MVP Features (Phase 1)

#### Data Collection & Processing

- **Automated Daily Collection**: Collect show data from phish.net, elgoose.net, and everydaycompanion.com
- **Data Standardization**: Transform raw data into consistent format for modeling
- **Error Handling**: Continue operations with existing data when sources fail
- **Email Notifications**: Alert administrator of collection failures

#### Prediction Engine

- **Notebook Model Implementation**: Deploy rotation-based prediction model as MVP
- **Next Song Predictions**: Generate probability rankings for next likely songs
- **Multi-Band Support**: Run predictions for Phish, Goose, and WSP independently. The system is
  designed to be extensible, allowing for the addition of new bands by creating new data collector modules.
- **Accuracy Tracking**: Store and calculate prediction accuracy at show level

#### Website Experience

- **Band Selection**: Toggle between supported bands
- **Prediction Display**: Show next song probabilities with confidence scores
- **Historical Accuracy**: Display model performance trends over time
- **Responsive Design**: Support desktop and mobile viewing
- **Status**: The website at `apps/web` is the product surface. Streamlit has been retired.

#### Infrastructure

- **Cloud Database**: Store raw data and predictions in Supabase
- **Automated Pipeline**: GitHub Actions for daily execution
- **Modular Architecture**: Independent component updates without full system changes

### Phase 2 Features (Revised Roadmap)

Phase 2 focuses on high-engagement features for the community, interactive games, and deep-dive analytics, prioritizing feasible implementations over speculative features.

#### Active Exploration Areas

- **Real-Time Show Tracking**: Update predictions and provide live insights as shows progress (dependent on live setlist ingestion from APIs or social platforms like Bluesky/Twitter).
- **Community Games**: Interactive prediction games without heavy social networking overhead.
  - *Pick 5*: Users predict 5 songs for the upcoming show.
  - *Fantasy Sets*: Song drafting with scoring based on rarity or placement.
  - *Jamble*: A daily Wordle-style brain teaser based on song statistics.
- **Analytics & Insights**: Leverage existing data for new visualizations.
  - *Song Relationship Mapping*: Transition probabilities (e.g., how often does "Mike's Song" lead to "I Am Hydrogen").
  - *Venue-Specific Patterns*: Historical bias for specific songs or jams at iconic venues (MSG, Dick's, Red Rocks).

#### On Hold / Pre-requisite Required

- **Full Setlist & Encore Predictions**: Blocked until a new predictive model is developed that accounts for setlist positioning (openers, closers, encores).
- **Interactive Setlist Builder**: On hold pending clear user demand.

---

## Functional Requirements

### Data Requirements

#### Data Collection

- **FR-DC-01**: System SHALL collect Phish show data from phish.net API daily
- **FR-DC-02**: System SHALL collect Goose show data from elgoose.net API daily
- **FR-DC-03**: System SHALL scrape WSP show data from everydaycompanion.com daily
- **FR-DC-04**: System SHALL store raw data in band-specific Supabase tables
- **FR-DC-05**: System SHALL handle API failures gracefully without stopping pipeline
- **FR-DC-06**: System SHALL send email notifications for persistent collection failures

#### Data Processing

- **FR-DP-01**: System SHALL transform raw data into standardized format for modeling
- **FR-DP-02**: System SHALL validate data integrity before model processing
- **FR-DP-03**: System SHALL support incremental updates for individual bands
- **FR-DP-04**: System SHALL maintain data lineage for debugging and auditing

### Prediction Requirements

#### Model Execution

- **FR-PE-01**: System SHALL generate next song predictions using Notebook model
- **FR-PE-02**: System SHALL calculate prediction probabilities for top 10 likely songs
- **FR-PE-03**: System SHALL store predictions with timestamps in Supabase
- **FR-PE-04**: System SHALL run predictions for all bands independently
- **FR-PE-05**: System SHALL support multiple prediction models simultaneously

#### Accuracy Tracking

- **FR-AT-01**: System SHALL calculate prediction accuracy at show level
- **FR-AT-02**: System SHALL track multiple accuracy metrics (top-1, top-3, top-5)
- **FR-AT-03**: System SHALL store accuracy history for trend analysis
- **FR-AT-04**: System SHALL update accuracy scores when new show data is available

### Interface Requirements

#### Website

- **FR-WA-01**: Interface SHALL display current predictions for selected band
- **FR-WA-02**: Interface SHALL allow switching between available bands
- **FR-WA-03**: Interface SHALL show prediction confidence scores
- **FR-WA-04**: Interface SHALL display historical accuracy trends
- **FR-WA-05**: Interface SHALL be responsive for desktop and mobile devices
- **FR-WA-06**: Interface SHALL load within 3 seconds for prediction views
- **FR-WA-07**: Website SHALL read prediction data server-side from Supabase in v1
- **FR-WA-08**: Website SHALL not require a separate public API in v1

#### User Experience

- **FR-UX-01**: Interface SHALL require no user authentication for basic features
- **FR-UX-02**: Interface SHALL provide clear visual indicators for prediction confidence
- **FR-UX-03**: Interface SHALL include explanatory text for model interpretation
- **FR-UX-04**: Interface SHALL handle network failures gracefully with cached data

### System Requirements

#### Performance

- **FR-SY-01**: Data collection SHALL complete within 1 hour for all bands
- **FR-SY-02**: Prediction generation SHALL complete within 30 minutes per band
- **FR-SY-03**: Website SHALL support 100 concurrent users
- **FR-SY-04**: System SHALL maintain 99% uptime for prediction availability

#### Scalability

- **FR-SC-01**: System SHALL be designed to allow the addition of new bands by creating a new data
  collector module without requiring changes to the core prediction or orchestration pipelines.
- **FR-SC-02**: System SHALL support addition of new models without data pipeline changes
- **FR-SC-03**: Database SHALL handle 10,000 shows per band with sub-second query response

---

## Non-Functional Requirements

### Reliability

- Pipeline SHALL recover automatically from transient failures
- System SHALL maintain data consistency across all components
- Predictions SHALL be reproducible given identical input data

### Maintainability

- Components SHALL be independently deployable and testable
- Code SHALL follow established Python conventions and documentation standards
- System SHALL provide comprehensive logging for debugging and monitoring

### Security

- API keys and database credentials SHALL be stored securely
- System SHALL validate all external data inputs
- Database access SHALL use principle of least privilege

### Usability

- Interface SHALL be intuitive for users unfamiliar with data science concepts
- Error messages SHALL be user-friendly and actionable
- Help documentation SHALL be accessible within the interface

---

## Success Metrics

### Engagement Metrics

- **Daily Active Users**: 50+ users within first month
- **Session Duration**: Average 5+ minutes per session
- **Return Users**: 30% weekly return rate

### Accuracy Metrics

- **Next Song Accuracy**: >15% top-1 accuracy (baseline: random ~3%)
- **Model Improvement**: Measurable accuracy improvement over 3-month periods
- **Multi-Model Comparison**: Clear performance differentiation between models

### Technical Metrics

- **Pipeline Reliability**: 95% successful daily execution rate
- **Data Freshness**: Predictions updated within 24 hours of new show data
- **Response Time**: 95% of page loads under 2 seconds

### Business Metrics

- **Feature Adoption**: All MVP features used by 70% of active users
- **Band Coverage**: Predictions available for all 3 supported bands
- **Model Expansion**: Ready for Phase 2 model addition within 6 months

---

## Risk Assessment

### High Risk

- **API Changes**: Data sources may change APIs or access policies
  - *Mitigation*: Build resilient scrapers, maintain fallback data sources
- **Model Accuracy**: Predictions may not exceed random chance meaningfully
  - *Mitigation*: Start with proven Notebook model, validate against historical data

### Medium Risk

- **User Adoption**: Limited audience may not justify development effort
  - *Mitigation*: Focus on core jam band communities, gather early feedback
- **Infrastructure Costs**: Supabase and hosting costs may scale unexpectedly
  - *Mitigation*: Monitor usage patterns, implement data retention policies

### Low Risk

- **Technical Complexity**: Implementation may exceed timeline estimates
  - *Mitigation*: Modular development approach, MVP feature prioritization

---

## Dependencies

### External Dependencies

- **Supabase**: Database and backend services
- **phish.net API**: Phish show data access
- **GitHub Actions**: Automation infrastructure
- **Next.js**: Website framework target
- **Vercel**: Website hosting target

### Internal Dependencies

- **Existing Codebase**: Leverage current data collection and model implementations
- **Data Sources Documentation**: Complete API/scraping specifications
- **Model Validation**: Historical accuracy validation for confidence in predictions

---

## Timeline & Milestones

### Phase 1 (MVP) - 8 weeks

- **Week 1-2**: Database setup and data collection migration
- **Week 3-4**: Prediction pipeline development and testing
- **Week 5-6**: Website application development
- **Week 7-8**: Integration testing and automation setup

### Phase 2 - 12 weeks

- **Week 9-12**: CK+ model integration and comparison features
- **Week 13-16**: Advanced interface features and real-time capabilities
- **Week 17-20**: Community features and prediction challenges

---

## Appendices

### Appendix A: API Rate Limits

- phish.net: 1000 requests/day
- elgoose.net: No published limits
- everydaycompanion.com: Respectful scraping practices

### Appendix B: Data Volume Estimates

- Phish: ~2,000 historical shows, ~100 shows/year
- Goose: ~500 historical shows, ~150 shows/year
- WSP: ~3,000 historical shows, ~80 shows/year

### Appendix C: Model Performance Baselines

- Random Prediction: ~3% next-song accuracy
- Current Notebook Model: ~12-18% accuracy (estimated)
- Target Improvement: 20%+ accuracy consistently
