"""Finalize per-band workflow status and gate consumers on validated data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def build_band_status(
    *, band: str, steps: dict[str, Any], job_status: str, accuracy_skipped: bool
) -> dict[str, Any]:
    """Build the final artifact from actual GitHub step outcomes and outputs."""

    def outputs(step: str) -> dict[str, str]:
        return steps.get(step, {}).get("outputs", {})

    def outcome(step: str) -> str:
        return steps.get(step, {}).get("outcome", "unknown")

    preflight = outputs("preflight")
    should_collect = preflight.get("should_run_collection") == "true"
    collection_step = "collection" if should_collect else "collection_idle"
    collection = outputs(collection_step)
    collection_state = collection.get("workflow_state", "unknown")
    collection_code = collection.get("outcome_code", "unknown")
    missing_data = outputs("data_check").get("missing_data") == "true"
    recent_data_usable = collection.get("recent_data_usable") == "true"
    degraded = collection_state == "degraded" or missing_data
    upcoming = outputs("show_target").get("has_upcoming_show") == "true"
    regenerate = should_collect and not degraded and collection_state == "success"

    required = ["preflight", collection_step, "data_check", "show_target"]
    if should_collect:
        required += [
            "freshness_audit",
            "supabase_audit",
            "freshness_enforcement",
            "cache_revalidation",
        ]
    if regenerate and upcoming:
        required += ["predictions", "prediction_validation"]
    if regenerate and not accuracy_skipped:
        required += ["accuracy_calc", "accuracy_validation"]
    failures = [step for step in required if outcome(step) != "success"]
    # A successful exit without the required decision/report outputs is not a pass.
    for step, key, allowed in [
        ("preflight", "should_run_collection", {"true", "false"}),
        (collection_step, "workflow_state", {"success", "degraded"}),
        ("data_check", "missing_data", {"true", "false"}),
        ("show_target", "has_upcoming_show", {"true", "false"}),
    ]:
        if outputs(step).get(key) not in allowed:
            failures.append(f"{step}.{key}")
    if should_collect:
        if outputs("freshness_audit").get("freshness_state") not in {
            "fresh",
            "warning",
        }:
            failures.append("freshness_audit.freshness_state")
        if outputs("supabase_audit").get("audit_state") not in {"ok", "warning"}:
            failures.append("supabase_audit.audit_state")

    workflow_state = "degraded" if degraded else "success"
    outcome_code = collection_code
    if missing_data and collection_code == "success":
        outcome_code = "degraded_upstream_lag"
    reused_existing = outcome_code == "degraded_upstream_lag" or (
        recent_data_usable and not missing_data
    )
    if failures or job_status != "success":
        workflow_state = "failed"
        outcome_code = (
            collection_code if collection_state == "failed" else "failed_internal"
        )
    if outcome("predictions") == "success":
        prediction_action = "generated"
    elif degraded:
        prediction_action = "reused_existing" if reused_existing else "skipped"
    elif not should_collect:
        prediction_action = "skipped_idle"
    elif workflow_state == "failed":
        prediction_action = "skipped"
    else:
        prediction_action = "pending"

    failure_reason = collection.get("failure_reason", "")
    if failures:
        failure_reason = "; ".join(
            filter(
                None,
                [
                    failure_reason,
                    "Required stages failed or missing: " + ", ".join(failures),
                ],
            )
        )
    if job_status != "success":
        failure_reason = "; ".join(
            filter(None, [failure_reason, f"Job status: {job_status}"])
        )

    freshness = outputs("freshness_audit")
    audit = outputs("supabase_audit")
    payload: dict[str, Any] = {
        "band": band,
        "workflow_state": workflow_state,
        "outcome_code": outcome_code,
        "collection_workflow_state": collection_state,
        "collection_outcome_code": collection_code,
        "recent_data_usable": recent_data_usable and not missing_data,
        "missing_data": missing_data,
        "missing_count": int(outputs("data_check").get("missing_count", "0") or 0),
        "prediction_action": prediction_action,
        "prediction_validation_outcome": outcome("prediction_validation"),
        "cache_revalidation_outcome": outcome("cache_revalidation"),
        "collection_mode": preflight.get("collection_mode", "unknown"),
        "execution_mode": preflight.get("execution_mode", "unknown"),
        "should_run_collection": should_collect,
        "has_upcoming_show": upcoming,
        "last_successful_collection_at": preflight.get(
            "last_successful_collection_at", ""
        ),
        "failure_reason": failure_reason,
        "accuracy_skipped": accuracy_skipped,
        "freshness_state": freshness.get("freshness_state", "unknown"),
        "freshness_reason": freshness.get("freshness_reason", ""),
        "supabase_audit_state": audit.get("audit_state", "unknown"),
    }
    for key in (
        "recent_completed_show_count",
        "missing_recent_setlist_count",
        "upcoming_show_count",
    ):
        payload[key] = int(preflight.get(key, "0") or 0)
    for key in (
        "fallback_shows_filled",
        "fallback_setlists_collected",
        "collector_missing_setlists",
        "request_blocked_missing_setlists",
        "upstream_missing_setlists",
        "fallback_available_missing_setlists",
    ):
        payload[key] = int(collection.get(key, "0") or 0)
    for key in ("stale_prediction_models", "stale_accuracy_models"):
        payload[key] = [
            item.strip() for item in freshness.get(key, "").split(",") if item.strip()
        ]
    for key in ("max_prediction_age_hours", "max_accuracy_age_hours"):
        value = freshness.get(key)
        payload[key] = float(value) if value else None
    for key in ("audit_blocker_count", "audit_warning_count"):
        payload[f"supabase_{key}"] = int(audit.get(key, "0") or 0)
    return payload


def fantasy_goose_eligible(status: dict[str, Any]) -> bool:
    """Only submit a freshly generated, validated Goose board."""
    return (
        status.get("band") == "goose"
        and status.get("workflow_state") == "success"
        and status.get("prediction_action") == "generated"
        and status.get("prediction_validation_outcome") == "success"
        and status.get("supabase_audit_state") in {"ok", "warning"}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fantasy-gate", type=Path)
    args = parser.parse_args()
    if args.fantasy_gate:
        try:
            status = json.loads(args.fantasy_gate.read_text())
        except (OSError, ValueError):
            status = {}
        eligible = isinstance(status, dict) and fantasy_goose_eligible(status)
        output = f"should_play={str(eligible).lower()}"
        print(output)
        if github_output := os.environ.get("GITHUB_OUTPUT"):
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(output + "\n")
        return

    band = os.environ["BAND"]
    payload = build_band_status(
        band=band,
        steps=json.loads(os.environ["STEPS_JSON"]),
        job_status=os.environ["JOB_STATUS"],
        accuracy_skipped=os.environ.get("ACCURACY_SKIPPED") == "true",
    )
    path = Path(f".github/workflow-status/{band}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"### {band.upper()}\n")
            for key in (
                "execution_mode",
                "workflow_state",
                "outcome_code",
                "prediction_action",
                "prediction_validation_outcome",
                "freshness_state",
                "supabase_audit_state",
                "cache_revalidation_outcome",
                "failure_reason",
            ):
                handle.write(f"- {key}: {payload[key]}\n")
    print(json.dumps(payload))
    if payload["workflow_state"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
