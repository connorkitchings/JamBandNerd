"""Unit tests for WSP CollectionStatus tracking."""

from jambandnerd.data_collection.wsp.status import CollectionStatus


class TestCollectionStatus:
    """Test suite for CollectionStatus class."""

    def test_initialization(self):
        """Test that CollectionStatus initializes with zero values."""
        status = CollectionStatus()
        assert status.http_403_errors == 0
        assert status.other_http_errors == 0
        assert status.songs_collected == 0
        assert status.shows_collected == 0
        assert status.setlists_collected == 0
        assert status.critical_failures == []

    def test_record_403_error(self):
        """Test recording 403 errors."""
        status = CollectionStatus()
        status.record_403_error("songs page")
        assert status.http_403_errors == 1
        assert len(status.critical_failures) == 1
        assert "403 Forbidden: songs page" in status.critical_failures

    def test_record_http_error(self):
        """Test recording non-403 HTTP errors."""
        status = CollectionStatus()
        status.record_http_error("tour page", 500)
        assert status.other_http_errors == 1
        assert len(status.critical_failures) == 1
        assert "HTTP 500: tour page" in status.critical_failures

    def test_should_fail_with_403_and_no_data(self):
        """Test that collection fails when 403s occur and no data collected."""
        status = CollectionStatus()
        status.record_403_error("songs endpoint")
        status.record_403_error("shows endpoint")
        status.songs_collected = 0
        status.shows_collected = 0
        assert status.should_fail() is False
        assert status.workflow_state() == "degraded"
        assert status.outcome_code() == "degraded_upstream_blocked"

    def test_should_not_fail_with_403_and_only_songs(self):
        """Test that collection succeeds when 403s occur but songs were collected."""
        status = CollectionStatus()
        status.record_403_error("shows endpoint")
        status.songs_collected = 100
        status.shows_collected = 0
        # Should NOT fail because songs_collected > 0 (site is reachable)
        assert status.should_fail() is False

    def test_should_not_fail_with_403_but_data_collected(self):
        """Test that collection succeeds when 403s occur but data was collected."""
        status = CollectionStatus()
        status.record_403_error("some endpoint")
        status.songs_collected = 100
        status.shows_collected = 10
        assert status.should_fail() is False

    def test_should_not_fail_with_no_errors(self):
        """Test that collection succeeds when no errors occur."""
        status = CollectionStatus()
        status.songs_collected = 100
        status.shows_collected = 50
        status.setlists_collected = 200
        assert status.should_fail() is False

    def test_should_fail_with_many_http_errors_and_no_shows(self):
        """Test that collection fails with many HTTP errors and no shows."""
        status = CollectionStatus()
        for i in range(6):  # More than threshold of 5
            status.record_http_error(f"endpoint {i}", 500)
        status.shows_collected = 0
        assert status.should_fail() is False
        assert status.workflow_state() == "degraded"
        assert status.outcome_code() == "degraded_upstream_blocked"

    def test_should_not_fail_with_few_http_errors(self):
        """Test that collection succeeds with few HTTP errors."""
        status = CollectionStatus()
        for i in range(3):  # Less than threshold of 5
            status.record_http_error(f"endpoint {i}", 500)
        status.shows_collected = 0
        assert status.should_fail() is False

    def test_get_failure_summary(self):
        """Test failure summary generation."""
        status = CollectionStatus()
        status.record_403_error("songs page")
        status.record_403_error("shows page")
        status.record_http_error("setlist page", 500)
        status.songs_collected = 0
        status.shows_collected = 0
        status.setlists_collected = 0

        summary = status.get_failure_summary()
        assert "Critical WSP collection failure" in summary
        assert "403 Forbidden errors: 2" in summary
        assert "Other HTTP errors: 1" in summary
        assert "Songs collected: 0" in summary
        assert "Shows collected: 0" in summary
        assert "Setlists collected: 0" in summary
        assert "Recent failures:" in summary

    def test_collector_missing_setlists_is_internal_failure(self):
        """Collector gaps should remain hard failures."""
        status = CollectionStatus()
        status.collector_missing_setlists = 1

        assert status.should_fail() is True
        assert status.workflow_state() == "failed"
        assert status.outcome_code() == "failed_internal"

    def test_request_blocked_recent_gap_is_degraded_stale(self):
        """Recent blocked setlists should be hard failures when data is unusable."""
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 2

        assert status.should_fail() is True
        assert status.workflow_state() == "failed"
        assert status.outcome_code() == "failed_upstream_stale"

    def test_upstream_missing_recent_setlist_is_degraded_lag(self):
        """Upstream lag (EC has not published yet) should degrade, not fail."""
        status = CollectionStatus()
        status.upstream_missing_setlists = 1

        assert status.outcome_code() == "degraded_upstream_lag"
        assert status.workflow_state() == "degraded"
        assert status.should_fail() is False
        assert status.should_retry_collection() is False
        assert status.has_recent_data_gap() is True

    def test_fallback_available_recent_setlist_is_degraded_lag(self):
        """Fallback-only recent coverage should degrade, not fail."""
        status = CollectionStatus()
        status.fallback_available_missing_setlists = 1

        assert status.outcome_code() == "degraded_upstream_lag"
        assert status.workflow_state() == "degraded"
        assert status.should_fail() is False

    def test_request_blocked_takes_precedence_over_upstream_missing(self):
        """True EC blocking stays a hard failure even with mixed diagnoses."""
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 1
        status.upstream_missing_setlists = 2

        assert status.outcome_code() == "failed_upstream_stale"
        assert status.workflow_state() == "failed"
        assert status.should_fail() is True

    def test_as_github_outputs_reports_machine_readable_state(self):
        """GitHub outputs should reflect the workflow-consumable status."""
        status = CollectionStatus()
        status.record_403_error("shows endpoint")
        status.songs_collected = 100
        status.set_prediction_action("reused_existing")

        outputs = status.as_github_outputs()

        assert outputs["workflow_state"] == "success"
        assert outputs["outcome_code"] == "success"
        assert outputs["prediction_action"] == "reused_existing"

    def test_get_failure_summary_limits_failures(self):
        """Test that failure summary only shows last 5 failures."""
        status = CollectionStatus()
        for i in range(10):
            status.record_403_error(f"endpoint {i}")

        summary = status.get_failure_summary()
        # Should only show last 5
        assert "endpoint 9" in summary
        assert "endpoint 5" in summary
        assert "endpoint 4" not in summary

    def test_get_success_summary(self):
        """Test success summary generation."""
        status = CollectionStatus()
        status.songs_collected = 100
        status.shows_collected = 50
        status.setlists_collected = 200

        summary = status.get_success_summary()
        assert "WSP collection completed successfully" in summary
        assert "Outcome code: success" in summary
        assert "Songs collected: 100" in summary
        assert "Shows collected: 50" in summary
        assert "Setlists collected: 200" in summary

    def test_get_success_summary_with_some_errors(self):
        """Test success summary when there were some errors but data was collected."""
        status = CollectionStatus()
        status.record_403_error("one endpoint")
        status.record_http_error("another endpoint", 500)
        status.songs_collected = 100
        status.shows_collected = 50
        status.setlists_collected = 200

        summary = status.get_success_summary()
        assert "WSP collection completed successfully" in summary
        assert "Some errors occurred but data was still collected" in summary
        assert "403 errors: 1" in summary
        assert "Other HTTP errors: 1" in summary

    def test_get_degraded_summary(self):
        """Degraded summary should include fallback and prediction behavior."""
        status = CollectionStatus()
        status.record_403_error("shows page")
        status.fallback_shows_filled = 2
        status.set_prediction_action("reused_existing")

        summary = status.get_degraded_summary()

        assert "WSP collection degraded due to upstream blocking" in summary
        assert "Outcome code: degraded_upstream_blocked" in summary
        assert "Recent fallback shows filled: 2" in summary
        assert "Prediction action: reused_existing" in summary
