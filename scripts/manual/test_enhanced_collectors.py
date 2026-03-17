#!/usr/bin/env python3
"""
Manual smoke-test script for the enhanced data collection system.

This is not part of the automated pytest suite. It exists as a quick way to validate
collector configuration and basic collection behavior when debugging locally.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path when executed directly
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.jambandnerd.data_collection.config import get_collector_config  # noqa: E402
from src.jambandnerd.data_collection.goose.collector import GooseCollector  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_config_system() -> bool:
    logger.info("Testing configuration system...")
    try:
        goose_config = get_collector_config("goose")
        logger.info("Goose config loaded: API URL = %s", goose_config.base_url)
        logger.info(
            "Rate limit: %s/%ss",
            goose_config.rate_limit_calls,
            goose_config.rate_limit_window,
        )

        phish_config = get_collector_config("phish")
        logger.info("Phish config loaded: API URL = %s", phish_config.base_url)
        logger.info(
            "Rate limit: %s/%ss",
            phish_config.rate_limit_calls,
            phish_config.rate_limit_window,
        )

        logger.info("✅ Configuration system test passed")
        return True
    except Exception as exc:
        logger.error("❌ Configuration system test failed: %s", exc)
        return False


def test_goose_collector() -> bool:
    logger.info("Testing Goose collector...")
    try:
        collector = GooseCollector()
        logger.info("Goose collector initialized successfully")

        logger.info("Testing song collection...")
        songs = collector.collect_songs()
        logger.info("Collected %s songs", len(songs))
        if songs:
            logger.info("First song sample: %s", songs[0].get("name", "N/A"))

        logger.info("✅ Goose collector test passed")
        return True
    except Exception as exc:
        logger.error("❌ Goose collector test failed: %s", exc)
        return False


def main() -> None:
    logger.info("Starting enhanced collector tests...")
    ok = True
    ok = test_config_system() and ok

    if os.environ.get("SKIP_NETWORK") != "true":
        ok = test_goose_collector() and ok
    else:
        logger.info("Skipping networked collector tests (SKIP_NETWORK=true)")

    if ok:
        logger.info("✅ All tests passed")
        raise SystemExit(0)
    logger.error("❌ One or more tests failed")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
