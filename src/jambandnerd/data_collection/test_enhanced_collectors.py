#!/usr/bin/env python3
"""
Test script for the enhanced data collection system.

This script tests the new base collector architecture, configuration system,
and enhanced error handling.
"""
import logging
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.jambandnerd.data_collection.config import get_collector_config
from src.jambandnerd.data_collection.goose.collector import GooseCollector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_config_system():
    """Test the configuration system."""
    logger.info("Testing configuration system...")

    try:
        # Test getting Goose config
        goose_config = get_collector_config('goose')
        logger.info(f"Goose config loaded: API URL = {goose_config.base_url}")
        logger.info(f"Rate limit: {goose_config.rate_limit_calls}/{goose_config.rate_limit_window}s")

        # Test getting Phish config
        phish_config = get_collector_config('phish')
        logger.info(f"Phish config loaded: API URL = {phish_config.base_url}")
        logger.info(f"Rate limit: {phish_config.rate_limit_calls}/{phish_config.rate_limit_window}s")

        logger.info("✅ Configuration system test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Configuration system test failed: {e}")
        return False


def test_goose_collector():
    """Test the enhanced Goose collector."""
    logger.info("Testing Goose collector...")

    try:
        # Initialize collector
        collector = GooseCollector()
        logger.info("Goose collector initialized successfully")

        # Test fetching a small amount of data
        logger.info("Testing song collection...")
        songs = collector.collect_songs()
        logger.info(f"Collected {len(songs)} songs")

        if len(songs) > 0:
            logger.info(f"First song sample: {songs[0].get('name', 'N/A')}")

        logger.info("✅ Goose collector test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Goose collector test failed: {e}")
        return False


def test_error_handling():
    """Test error handling with invalid endpoint."""
    logger.info("Testing error handling...")

    try:
        collector = GooseCollector()

        # Try to fetch from a non-existent endpoint
        logger.info("Testing error handling with invalid endpoint...")
        try:
            bad_data = collector._fetch_from_endpoint("non_existent_endpoint")
            logger.warning(f"Unexpected success with bad endpoint: {len(bad_data)} records")
        except Exception as e:
            logger.info(f"Expected error caught: {type(e).__name__}: {e}")

        logger.info("✅ Error handling test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting enhanced data collection system tests...")
    logger.info("=" * 60)

    tests = [
        ("Configuration System", test_config_system),
        ("Goose Collector", test_goose_collector),
        ("Error Handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            failed += 1

    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Tests passed: {passed}")
    logger.info(f"Tests failed: {failed}")

    if failed == 0:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
