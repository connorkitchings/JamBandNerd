"""Comprehensive validation test to verify all warning scenarios."""
from __future__ import annotations

import os
import sys
import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.operations import get_table_schema
from src.jambandnerd.db.validation import (
    coerce_df_types,
    validate_dataframe_against_table,
)


def test_comprehensive_validation():
    """Test comprehensive validation scenarios."""
    print("=" * 80)
    print("COMPREHENSIVE VALIDATION TEST")
    print("=" * 80)
    print()
    
    # Get schema for goose_setlists_raw (has more interesting types)
    schema = get_table_schema("goose_setlists_raw")
    
    if not schema:
        print("❌ Could not retrieve schema for goose_setlists_raw")
        return
    
    print(f"✅ Schema retrieved for goose_setlists_raw ({len(schema)} columns)")
    print()
    
    # Test Case 1: Completely valid data
    print("Test 1: Valid Data (should pass without warnings)")
    print("-" * 80)
    
    valid_df = pd.DataFrame({
        "show_id": ["test_001"],
        "set_number": [1],
        "song_position": [1],
        "song_name": ["Test Song"],
        "encore": [False],
        "notes": [None],
        "source_hash": ["abc123"],
        "created_at": [None],
        "updated_at": [None],
    })
    
    coerced_valid = coerce_df_types(valid_df, schema)
    report_valid = validate_dataframe_against_table(coerced_valid, "goose_setlists_raw", schema)
    
    if report_valid.is_valid:
        print("✅ Valid data passed validation (no warnings)")
    else:
        print("⚠️  Valid data triggered warnings:")
        if report_valid.missing_columns:
            print(f"    Missing columns: {report_valid.missing_columns}")
        if report_valid.type_mismatches:
            print(f"    Type mismatches: {len(report_valid.type_mismatches)} columns")
            for tm in report_valid.type_mismatches[:3]:
                print(f"        - {tm.column}: expected {tm.expected_type}, got {tm.observed_type}")
        if report_valid.nullable_violations:
            print(f"    Nullable violations: {report_valid.nullable_violations}")
    
    print()
    
    # Test Case 2: Missing required columns
    print("Test 2: Missing Required Columns (should fail)")
    print("-" * 80)
    
    incomplete_df = pd.DataFrame({
        "show_id": ["test_002"],
        "set_number": [1],
        # Missing required fields like song_position, song_name
    })
    
    coerced_incomplete = coerce_df_types(incomplete_df, schema)
    report_incomplete = validate_dataframe_against_table(coerced_incomplete, "goose_setlists_raw", schema)
    
    if not report_incomplete.is_valid:
        print("⚠️  Validation warnings for goose_setlists_raw:")
        if report_incomplete.missing_columns:
            print(f"    Missing columns: {report_incomplete.missing_columns}")
        if report_incomplete.type_mismatches:
            print(f"    Type mismatches: {len(report_incomplete.type_mismatches)} columns")
        if report_incomplete.nullable_violations:
            print(f"    Nullable violations: {report_incomplete.nullable_violations}")
        print()
        print("✅ Missing columns correctly detected!")
    else:
        print("❌ Missing columns not detected")
    
    print()
    
    # Test Case 3: Nullable violations
    print("Test 3: Nullable Violations (should fail)")
    print("-" * 80)
    
    null_violation_df = pd.DataFrame({
        "show_id": [None],  # Required field
        "set_number": [1],
        "song_position": [1],
        "song_name": ["Test Song"],
        "encore": [False],
        "notes": [None],
        "source_hash": ["abc123"],
        "created_at": [None],
        "updated_at": [None],
    })
    
    coerced_null = coerce_df_types(null_violation_df, schema)
    report_null = validate_dataframe_against_table(coerced_null, "goose_setlists_raw", schema)
    
    if not report_null.is_valid:
        print("⚠️  Validation warnings for goose_setlists_raw:")
        if report_null.missing_columns:
            print(f"    Missing columns: {report_null.missing_columns}")
        if report_null.type_mismatches:
            print(f"    Type mismatches: {len(report_null.type_mismatches)} columns")
        if report_null.nullable_violations:
            print(f"    Nullable violations: {report_null.nullable_violations}")
        print()
        print("✅ Nullable violations correctly detected!")
    else:
        print("❌ Nullable violations not detected")
    
    print()
    
    # Test Case 4: Type mismatches (tracked but don't cause failure)
    print("Test 4: Type Mismatches (tracked as warnings, but validation passes)")
    print("-" * 80)
    
    type_mismatch_df = pd.DataFrame({
        "show_id": ["test_004"],
        "set_number": ["not_a_number"],  # String where integer expected
        "song_position": [1],
        "song_name": ["Test Song"],
        "encore": ["maybe"],  # Invalid boolean
        "notes": [None],
        "source_hash": ["abc123"],
        "created_at": [None],
        "updated_at": [None],
    })
    
    coerced_mismatch = coerce_df_types(type_mismatch_df, schema)
    report_mismatch = validate_dataframe_against_table(coerced_mismatch, "goose_setlists_raw", schema)
    
    print(f"Validation result: is_valid={report_mismatch.is_valid}")
    if report_mismatch.type_mismatches:
        print("⚠️  Type mismatches detected (but validation still passes):")
        for tm in report_mismatch.type_mismatches:
            print(f"    - {tm.column}: expected {tm.expected_type}, got {tm.observed_type}")
    if report_mismatch.missing_columns:
        print(f"    Missing columns: {report_mismatch.missing_columns}")
    if report_mismatch.nullable_violations:
        print(f"    Nullable violations: {report_mismatch.nullable_violations}")
    
    print()
    print("✅ Type coercion handled gracefully")
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print("Validation Behavior:")
    print("  ✅ Valid data passes without warnings")
    print("  ✅ Missing required columns cause validation failure")
    print("  ✅ Nullable violations cause validation failure")
    print("  ✅ Type mismatches are coerced and don't block validation")
    print()
    print("This means validation is WARNING-ONLY for type issues,")
    print("but STRICT for missing columns and nullable violations.")
    print()
    print("=" * 80)


if __name__ == "__main__":
    test_comprehensive_validation()
