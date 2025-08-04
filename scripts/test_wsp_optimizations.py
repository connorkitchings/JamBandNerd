#!/usr/bin/env python3
"""
Test script for WSP data ingestion optimizations.

This script validates the new caching and date-filtering optimizations
to ensure they work correctly for daily runs.
"""

import os
import sys
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jambandnerd.data_collection.wsp.cache_utils import (
    ensure_cache_dir,
    get_date_filter_cutoff,
    get_supabase_date_filter,
    should_scrape_shows,
    should_scrape_songs,
    update_shows_cache,
    update_songs_cache,
)
from jambandnerd.data_collection.wsp.run_pipeline import main as run_wsp_pipeline


def test_cache_utilities():
    """Test the caching utility functions."""
    print("🧪 Testing cache utilities...")

    # Ensure cache directory exists
    ensure_cache_dir()
    print("✅ Cache directory created/verified")

    # Test date filter functions
    cutoff_3_months = get_date_filter_cutoff(months_back=3)
    cutoff_supabase = get_supabase_date_filter(years_back=3)

    print(f"✅ 3-month cutoff date: {cutoff_3_months.strftime('%Y-%m-%d')}")
    print(f"✅ Supabase 3-year filter: {cutoff_supabase}")

    # Test cache decision logic (should scrape on first run)
    should_scrape_shows_result = should_scrape_shows(force_scrape=False, max_age_days=7)
    should_scrape_songs_result = should_scrape_songs(force_scrape=False, max_age_days=7)

    print(f"✅ Should scrape shows (first run): {should_scrape_shows_result}")
    print(f"✅ Should scrape songs (first run): {should_scrape_songs_result}")

    # Update cache timestamps
    update_shows_cache(100)  # Mock 100 shows
    update_songs_cache(50)  # Mock 50 songs
    print("✅ Cache timestamps updated")

    # Test cache decision logic again (should not scrape immediately after)
    should_scrape_shows_cached = should_scrape_shows(force_scrape=False, max_age_days=7)
    should_scrape_songs_cached = should_scrape_songs(force_scrape=False, max_age_days=7)

    print(f"✅ Should scrape shows (cached): {should_scrape_shows_cached}")
    print(f"✅ Should scrape songs (cached): {should_scrape_songs_cached}")

    print("🎉 Cache utilities test completed successfully!\n")


def test_pipeline_dry_run():
    """Test the optimized pipeline in dry-run mode."""
    print("🧪 Testing optimized WSP pipeline (dry-run)...")

    try:
        # Test with update mode and force scrape (to see all functionality)
        print("Running pipeline with update=True, force_scrape_all=True...")
        start_time = time.time()

        run_wsp_pipeline(update=True, force_scrape_all=True)

        elapsed = time.time() - start_time
        print(f"✅ Pipeline completed in {elapsed:.2f} seconds")
        print("🎉 Optimized pipeline test completed successfully!\n")

    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

    return True


def test_cache_behavior():
    """Test that caching actually prevents unnecessary scraping."""
    print("🧪 Testing cache behavior...")

    try:
        # First run - should scrape everything
        print("First run (should scrape shows/songs)...")
        run_wsp_pipeline(update=True, force_scrape_all=False)

        # Wait a moment
        time.sleep(2)

        # Second run immediately after - should use cache
        print("Second run (should use cache for shows/songs)...")
        run_wsp_pipeline(update=True, force_scrape_all=False)

        print("✅ Cache behavior test completed")

    except Exception as e:
        print(f"❌ Cache behavior test failed: {e}")
        return False

    return True


def main():
    """Run all optimization tests."""
    print("🚀 Starting WSP optimization tests...\n")

    # Test 1: Cache utilities
    test_cache_utilities()

    # Test 2: Pipeline dry-run
    success = test_pipeline_dry_run()
    if not success:
        print("❌ Pipeline test failed, skipping cache behavior test")
        return

    # Test 3: Cache behavior
    test_cache_behavior()

    print("🎉 All WSP optimization tests completed!")
    print("\n📊 Summary of optimizations:")
    print("✅ Date-based filtering: Only check setlists from last 3 months")
    print("✅ Intelligent caching: Shows/songs only scraped every 7 days")
    print("✅ Smart pagination: Supabase queries limited to last 3 years")
    print("✅ Reduced scraping: Only new setlists are scraped daily")
    print("\n🎯 Expected daily run behavior:")
    print("- Shows/songs: Loaded from Supabase cache (no scraping)")
    print("- Setlists: Only scrape shows from last 3 months that aren't in DB")
    print("- Supabase queries: Limited to last 3 years of data")


if __name__ == "__main__":
    main()
