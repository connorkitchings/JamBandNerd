# Testing Guide

This directory contains the test suite for JamBandNerd.

## Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_data_collection.py` - Tests for data collection modules
- `test_models.py` - Tests for prediction models
- `test_db.py` - Tests for database operations
- `data/` - Sample data files for testing

## Running Tests

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests for a specific module
pytest tests/test_models.py

# Run tests with coverage (when pytest-cov is installed)
pytest --cov=src/jambandnerd

# Run tests matching a pattern
pytest -k "test_prediction"
```

## Test Organization

Tests are organized by module, with each test file corresponding to a source module. Mock implementations are used to test abstract base classes and avoid external dependencies during testing.

## Fixtures

Common test fixtures are defined in `conftest.py`:

- `project_root` - Path to the project root directory
- `sample_data_dir` - Path to test data directory  
- `mock_env_vars` - Mock environment variables for testing
- `setup_test_env` - Sets up test environment variables

## Sample Data

The `data/` directory contains sample JSON files that can be used in tests to simulate API responses and database records.
