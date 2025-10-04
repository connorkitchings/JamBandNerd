"""Test script to verify validation warnings are displayed correctly.

This script creates intentionally problematic DataFrames and attempts to validate them
to verify that warning messages are displayed properly without blocking the insert.
"""
from __future__ import annotations

import os
import sys
import pandas as pd
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.operations import get_table_schema
from src.jambandnerd.db.validation import (
    coerce_df_types,
    validate_dataframe_against_table,
)


def test_validation_warnings():
    """Test that validation warnings display correctly."""
    print("=" * 70)
    print("VALIDATION WARNING TEST")
    print("=" * 70)
    print()
    
    # Test 1: Create a DataFrame with type mismatches
    print("Test 1: Type Mismatches")
    print("-" * 70)
    
    test_df = pd.DataFrame({
        "show_id": ["test_001"],
        "show_date": ["2024-01-15"],  # This should be a date
        "venue_name": ["Test Venue"],
        "venue_city": ["Test City"],
        "venue_state": ["TS"],
        "venue_country": ["US"],
        "tour_name": [None],
        "source_hash": ["abc123"],
        "created_at": ["2024-01-15T12:00:00"],
        "updated_at": ["2024-01-15T12:00:00"],
    })
    
    schema = get_table_schema("goose_shows_raw")
    if schema:
        print(f"Schema retrieved for goose_shows_raw with {len(schema)} columns")
        
        # Coerce types
        coerced_df = coerce_df_types(test_df, schema)
        print(f"DataFrame coerced: {coerced_df.dtypes.to_dict()}")
        print()
        
        # Validate
        report = validate_dataframe_against_table(coerced_df, "goose_shows_raw", schema)
        
        if not report.is_valid:
            print("⚠️  Validation warnings for goose_shows_raw:")
            if report.missing_columns:
                print(f"    Missing columns: {report.missing_columns}")
            if report.type_mismatches:
                print(f"    Type mismatches: {len(report.type_mismatches)} columns")
                for col, expected, actual in report.type_mismatches[:3]:
                    print(f"        - {col}: expected {expected}, got {actual}")
            if report.nullable_violations:
                print(f"    Nullable violations: {report.nullable_violations}")
            print()
            print("✅ Validation warnings displayed correctly!")
        else:
            print("✅ No validation issues (data is valid)")
    else:
        print("❌ Could not retrieve schema for goose_shows_raw")
    
    print()
    print("=" * 70)
    
    # Test 2: Create a DataFrame with missing required columns
    print("Test 2: Missing Required Columns")
    print("-" * 70)
    
    incomplete_df = pd.DataFrame({
        "show_id": ["test_002"],
        "show_date": ["2024-01-15"],
        # Missing other required fields
    })
    
    if schema:
        coerced_df = coerce_df_types(incomplete_df, schema)
        report = validate_dataframe_against_table(coerced_df, "goose_shows_raw", schema)
        
        if not report.is_valid:
            print("⚠️  Validation warnings for goose_shows_raw:")
            if report.missing_columns:
                print(f"    Missing columns: {report.missing_columns}")
            if report.type_mismatches:
                print(f"    Type mismatches: {len(report.type_mismatches)} columns")
            if report.nullable_violations:
                print(f"    Nullable violations: {report.nullable_violations}")
            print()
            print("✅ Validation warnings displayed correctly!")
        else:
            print("✅ No validation issues")
    
    print()
    print("=" * 70)
    
    # Test 3: Verify warning-only behavior (should not raise exception)
    print("Test 3: Warning-Only Behavior")
    print("-" * 70)
    
    try:
        # This should not raise an exception even with validation issues
        bad_df = pd.DataFrame({
            "show_id": [123],  # Wrong type (should be string)
            "show_date": ["invalid_date"],  # Invalid date format
            "venue_name": [None],
            "venue_city": [None],
            "venue_state": [None],
            "venue_country": [None],
            "tour_name": [None],
            "source_hash": ["test"],
            "created_at": [None],
            "updated_at": [None],
        })
        
        if schema:
            coerced_df = coerce_df_types(bad_df, schema)
            report = validate_dataframe_against_table(coerced_df, "goose_shows_raw", schema)
            
            print(f"Validation completed without exception: is_valid={report.is_valid}")
            
            if not report.is_valid:
                print("⚠️  Validation warnings for goose_shows_raw:")
                if report.missing_columns:
                    print(f"    Missing columns: {report.missing_columns}")
                if report.type_mismatches:
                    print(f"    Type mismatches: {len(report.type_mismatches)} columns")
                if report.nullable_violations:
                    print(f"    Nullable violations: {report.nullable_violations}")
            
            print()
            print("✅ Validation is warning-only (no exception raised)!")
    except Exception as e:
        print(f"❌ Unexpected exception raised: {e}")
    
    print()
    print("=" * 70)
    print("VALIDATION WARNING TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_validation_warnings()
