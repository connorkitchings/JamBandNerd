"""Status tracking for WSP data collection to determine success/failure."""

from __future__ import annotations

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
        self.fallback_setlists_collected = 0
        self.fallback_shows_filled = 0
        self.upstream_missing_setlists = 0
        self.collector_missing_setlists = 0
        self.request_blocked_missing_setlists = 0
        self.fallback_available_missing_setlists = 0
        self.critical_failures: List[str] = []
        self.prediction_action = "pending"

    def _has_systemic_http_failure(self) -> bool:
        """Return True when the collector appears blocked upstream."""
        if (
            self.http_403_errors > 0
            and self.songs_collected == 0
            and self.shows_collected == 0
        ):
            logger.warning(
                "Collection hit 403s with zero songs and zero shows collected"
            )
            return True

        if self.other_http_errors > 5 and self.shows_collected == 0:
            logger.warning(
                "Collection hit %s HTTP errors with zero shows collected",
                self.other_http_errors,
            )
            return True

        return False

    def has_recent_data_gap(self) -> bool:
        """Return True when recent completed-show data is still incomplete."""
        return (
            self.upstream_missing_setlists > 0
            or self.collector_missing_setlists > 0
            or self.request_blocked_missing_setlists > 0
            or self.fallback_available_missing_setlists > 0
        )

    def outcome_code(self) -> str:
        """Classify the collection run for CI/workflow branching."""
        if self.collector_missing_setlists > 0:
            return "failed_internal"

        if self.request_blocked_missing_setlists > 0:
            # When the EC page itself is unreachable and fallback sources
            # also come up empty for a very recent show, the collector
            # still produced usable data.  Degrade instead of hard-failing
            # — the pipeline reuses prior prediction data until the next
            # collection window when the upstreams have caught up.
            if self.shows_collected > 0 or self.songs_collected > 0:
                return "degraded_upstream_stale"
            return "failed_upstream_stale"

        if (
            self.upstream_missing_setlists > 0
            or self.fallback_available_missing_setlists > 0
        ):
            return "failed_upstream_stale"

        if self._has_systemic_http_failure():
            return "degraded_upstream_blocked"

        return "success"

    def workflow_state(self) -> str:
        """Return the coarse workflow state for summaries."""
        outcome = self.outcome_code()
        if outcome == "success":
            return "success"
        if outcome.startswith("degraded_"):
            return "degraded"
        return "failed"

    def should_retry_collection(self) -> bool:
        """Return True when retrying the whole collector run still makes sense."""
        return self.workflow_state() == "failed"

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

    def record_missing_setlist_diagnostic(self, diagnosis: str) -> None:
        """Record how a recent missing setlist was classified."""
        if diagnosis == "upstream_missing_setlist":
            self.upstream_missing_setlists += 1
        elif diagnosis == "collector_missed_setlist":
            self.collector_missing_setlists += 1
        elif diagnosis == "ec_request_failed":
            self.request_blocked_missing_setlists += 1
        elif diagnosis == "fallback_data_available":
            self.fallback_available_missing_setlists += 1

    def should_fail(self) -> bool:
        """Determine if collection should be considered a failure.

        Returns:
            True if the collection should fail (exit non-zero), False otherwise
        """
        return self.workflow_state() == "failed"

    def set_prediction_action(self, action: str) -> None:
        """Record how downstream predictions were handled for summary reporting."""
        self.prediction_action = action

    def as_github_outputs(self) -> dict[str, str]:
        """Return GitHub Actions-compatible outputs for the collection run."""
        return {
            "workflow_state": self.workflow_state(),
            "outcome_code": self.outcome_code(),
            "should_retry_collection": str(self.should_retry_collection()).lower(),
            "recent_data_usable": str(not self.has_recent_data_gap()).lower(),
            "prediction_action": self.prediction_action,
            "http_403_errors": str(self.http_403_errors),
            "other_http_errors": str(self.other_http_errors),
            "fallback_shows_filled": str(self.fallback_shows_filled),
            "fallback_setlists_collected": str(self.fallback_setlists_collected),
            "upstream_missing_setlists": str(self.upstream_missing_setlists),
            "collector_missing_setlists": str(self.collector_missing_setlists),
            "request_blocked_missing_setlists": str(
                self.request_blocked_missing_setlists
            ),
            "fallback_available_missing_setlists": str(
                self.fallback_available_missing_setlists
            ),
        }

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
            f"  - Recent fallback shows filled: {self.fallback_shows_filled}",
            f"  - Recent fallback setlists collected: {self.fallback_setlists_collected}",
        ]
        if self.critical_failures:
            lines.append("  Recent failures:")
            # Show last 5 failures to avoid overwhelming output
            for failure in self.critical_failures[-5:]:
                lines.append(f"    - {failure}")
        return "\n".join(lines)

    def get_degraded_summary(self) -> str:
        """Get a human-readable summary of a degraded-but-usable run."""
        lines = [
            "WSP collection degraded due to upstream blocking:",
            f"  - Outcome code: {self.outcome_code()}",
            f"  - 403 Forbidden errors: {self.http_403_errors}",
            f"  - Other HTTP errors: {self.other_http_errors}",
            f"  - Songs collected: {self.songs_collected}",
            f"  - Shows collected: {self.shows_collected}",
            f"  - Setlists collected: {self.setlists_collected}",
            f"  - Recent fallback shows filled: {self.fallback_shows_filled}",
            f"  - Recent fallback setlists collected: {self.fallback_setlists_collected}",
            f"  - Upstream pages without setlists: {self.upstream_missing_setlists}",
            "  - Collector-visible pages still missing in raw tables: "
            f"{self.collector_missing_setlists}",
            "  - EC request failures without fallback: "
            f"{self.request_blocked_missing_setlists}",
            "  - Fallback data available but not stored: "
            f"{self.fallback_available_missing_setlists}",
            f"  - Prediction action: {self.prediction_action}",
        ]
        if self.critical_failures:
            lines.append("  Recent failures:")
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
            f"  - Outcome code: {self.outcome_code()}",
            f"  - Songs collected: {self.songs_collected}",
            f"  - Shows collected: {self.shows_collected}",
            f"  - Setlists collected: {self.setlists_collected}",
            f"  - Prediction action: {self.prediction_action}",
        ]
        if self.fallback_setlists_collected > 0 or self.fallback_shows_filled > 0:
            lines.append("  - Recent fallback:")
            lines.append(f"    - Shows filled: {self.fallback_shows_filled}")
            lines.append(
                f"    - Setlist rows inserted: {self.fallback_setlists_collected}"
            )
        if self.http_403_errors > 0 or self.other_http_errors > 0:
            lines.append("  - Some errors occurred but data was still collected:")
            lines.append(f"    - 403 errors: {self.http_403_errors}")
            lines.append(f"    - Other HTTP errors: {self.other_http_errors}")
        if (
            self.upstream_missing_setlists > 0
            or self.collector_missing_setlists > 0
            or self.request_blocked_missing_setlists > 0
            or self.fallback_available_missing_setlists > 0
        ):
            lines.append("  - Recent missing-setlist diagnostics:")
            lines.append(
                f"    - Upstream pages without setlists: {self.upstream_missing_setlists}"
            )
            lines.append(
                "    - Collector-visible pages still missing in raw tables: "
                f"{self.collector_missing_setlists}"
            )
            lines.append(
                "    - EC request failures without fallback: "
                f"{self.request_blocked_missing_setlists}"
            )
            lines.append(
                "    - Fallback data available but not stored: "
                f"{self.fallback_available_missing_setlists}"
            )
        return "\n".join(lines)
