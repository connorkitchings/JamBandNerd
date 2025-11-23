"""Status tracking for WSP data collection to determine success/failure."""

import logging
from typing import List

logger = logging.getLogger(__name__)


class CollectionStatus:
    """Tracks the status of WSP data collection to determine success/failure.

    This class tracks HTTP errors and data collection counts to determine whether
    the collection run should be considered successful or should fail with a non-zero
    exit code. This is particularly important for CI/CD pipelines where silent failures
    (collecting zero data due to HTTP 403 errors but exiting with code 0) should be
    made visible.
    """

    def __init__(self):
        """Initialize collection status tracking."""
        self.http_403_errors = 0
        self.other_http_errors = 0
        self.songs_collected = 0
        self.shows_collected = 0
        self.setlists_collected = 0
        self.critical_failures: List[str] = []

    def record_403_error(self, context: str) -> None:
        """Record a 403 Forbidden error with context.

        Args:
            context: Description of what was being accessed when the error occurred
        """
        self.http_403_errors += 1
        self.critical_failures.append(f"403 Forbidden: {context}")
        logger.debug(f"Recorded 403 error: {context}")

    def record_http_error(self, context: str, status_code: int) -> None:
        """Record a non-403 HTTP error.

        Args:
            context: Description of what was being accessed when the error occurred
            status_code: The HTTP status code that was returned
        """
        self.other_http_errors += 1
        self.critical_failures.append(f"HTTP {status_code}: {context}")
        logger.debug(f"Recorded HTTP {status_code} error: {context}")

    def should_fail(self) -> bool:
        """Determine if collection should be considered a failure.

        Returns:
            True if the collection should fail (exit non-zero), False otherwise

        Logic:
            - If we have 403 errors and collected zero songs AND zero shows, fail
            - If we have many other HTTP errors (>5) and collected zero shows, fail
            - Otherwise, succeed (there may be legitimate cases of no new data)
        """
        # If we have 403 errors and collected zero data, fail
        if self.http_403_errors > 0:
            if self.songs_collected == 0 and self.shows_collected == 0:
                logger.warning(
                    f"Collection should fail: {self.http_403_errors} 403 errors "
                    f"with 0 songs and 0 shows collected"
                )
                return True

        # If we have other critical HTTP errors and no data, fail
        if self.other_http_errors > 5:  # Threshold for "too many errors"
            if self.shows_collected == 0:
                logger.warning(
                    f"Collection should fail: {self.other_http_errors} HTTP errors "
                    f"with 0 shows collected"
                )
                return True

        return False

    def get_failure_summary(self) -> str:
        """Get a human-readable summary of why collection failed.

        Returns:
            Multi-line string describing the failure state
        """
        lines = [
            "Critical WSP collection failure:",
            f"  - 403 Forbidden errors: {self.http_403_errors}",
            f"  - Other HTTP errors: {self.other_http_errors}",
            f"  - Songs collected: {self.songs_collected}",
            f"  - Shows collected: {self.shows_collected}",
            f"  - Setlists collected: {self.setlists_collected}",
        ]
        if self.critical_failures:
            lines.append("  Recent failures:")
            # Show last 5 failures to avoid overwhelming output
            for failure in self.critical_failures[-5:]:
                lines.append(f"    - {failure}")
        return "\n".join(lines)

    def get_success_summary(self) -> str:
        """Get a human-readable summary of successful collection.

        Returns:
            Multi-line string describing what was collected
        """
        lines = [
            "WSP collection completed successfully:",
            f"  - Songs collected: {self.songs_collected}",
            f"  - Shows collected: {self.shows_collected}",
            f"  - Setlists collected: {self.setlists_collected}",
        ]
        if self.http_403_errors > 0 or self.other_http_errors > 0:
            lines.append("  - Some errors occurred but data was still collected:")
            lines.append(f"    - 403 errors: {self.http_403_errors}")
            lines.append(f"    - Other HTTP errors: {self.other_http_errors}")
        return "\n".join(lines)
