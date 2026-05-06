"""Audit supported-model prediction and accuracy freshness for one band.

This script is intended for GitHub Actions and operator diagnostics. It reports
freshness for the currently supported model surfaces without failing simply
because rows are stale. Workflow enforcement should happen after status
artifacts and summaries are written.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from jambandnerd.config import (
    COMPLETED_SHOW_ACCURACY_TABLE,
    NEXT_SHOW_PREDICTION_RUNS_TABLE,
)
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.models.registry import (
    list_accuracy_validation_models,
    list_models,
)
from scripts.common import parse_timestamp
from scripts.validate_prediction_tables import _has_upcoming_show


@dataclass(frozen=True)
class SupportedModelFreshnessResult:
    band: str
    max_age_hours: int
    skip_accuracy: bool
    freshness_state: str
    stale_prediction_models: tuple[str, ...]
    stale_accuracy_models: tuple[str, ...]
    max_prediction_age_hours: float | None
    max_accuracy_age_hours: float | None
    freshness_reason: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["stale_prediction_models"] = list(self.stale_prediction_models)
        payload["stale_accuracy_models"] = list(self.stale_accuracy_models)
        return payload

    def as_github_outputs(self) -> dict[str, str]:
        return {
            "freshness_state": self.freshness_state,
            "stale_prediction_models": ",".join(self.stale_prediction_models),
            "stale_accuracy_models": ",".join(self.stale_accuracy_models),
            "max_prediction_age_hours": _format_hours_output(
                self.max_prediction_age_hours
            ),
            "max_accuracy_age_hours": _format_hours_output(self.max_accuracy_age_hours),
            "freshness_reason": self.freshness_reason,
        }


def _format_hours_output(value: float | None) -> str:
    return "" if value is None else f"{value:.1f}"


def _latest_timestamp_row(
    client,
    *,
    table: str,
    band: str,
    model_version: str,
    timestamp_field: str,
    model_slug: str | None = None,
):
    query = (
        client.table(table)
        .select(f"band, model_version, {timestamp_field}")
        .eq("band", band)
        .eq("model_version", model_version)
    )
    if model_slug:
        query = query.eq("model_slug", model_slug)
    rows = query.order(timestamp_field, desc=True).limit(1).execute().data or []
    return rows[0] if rows else None


def _evaluate_timestamp_row(
    *,
    row: dict[str, object] | None,
    timestamp_field: str,
    max_age_hours: int,
    now: datetime,
    missing_reason: str,
    invalid_reason: str,
    stale_reason_prefix: str,
) -> tuple[bool, float | None, str]:
    if not row:
        return True, None, missing_reason

    timestamp = parse_timestamp(str(row.get(timestamp_field) or ""))
    if timestamp is None:
        return True, None, invalid_reason

    age_hours = (now - timestamp).total_seconds() / 3600
    if age_hours > max_age_hours:
        return True, age_hours, f"{stale_reason_prefix} age={age_hours:.1f}h"

    return False, age_hours, ""


def _list_supported_prediction_models():
    return [
        definition
        for definition in list_models()
        if definition.enabled_for_pipeline or definition.enabled_for_web
    ]


def audit_supported_model_freshness(
    *,
    band: str,
    max_age_hours: int = 48,
    skip_accuracy: bool = False,
    emit_text: bool = True,
    client=None,
) -> SupportedModelFreshnessResult:
    client = client or get_supabase_client()
    now = datetime.now(timezone.utc)

    prediction_models = {
        definition.slug: definition
        for definition in _list_supported_prediction_models()
    }
    accuracy_models = {
        definition.slug: definition for definition in list_accuracy_validation_models()
    }

    stale_prediction_models: list[str] = []
    stale_accuracy_models: list[str] = []
    prediction_reasons: list[str] = []
    accuracy_reasons: list[str] = []
    prediction_ages: list[float] = []
    accuracy_ages: list[float] = []
    surface_lines: list[str] = []
    live_prediction_required = _has_upcoming_show(client, band=band)

    for slug in sorted(prediction_models):
        definition = prediction_models[slug]
        if not live_prediction_required:
            surface_lines.append(
                _render_surface_line(
                    slug=slug,
                    surface="predictions",
                    age_hours=None,
                    is_stale=False,
                    fallback_reason="no upcoming show; live prediction not required",
                )
            )
            continue
        row = _latest_timestamp_row(
            client,
            table=NEXT_SHOW_PREDICTION_RUNS_TABLE,
            band=band,
            model_version=definition.version,
            timestamp_field="generated_at",
            model_slug=definition.slug,
        )
        is_stale, age_hours, reason = _evaluate_timestamp_row(
            row=row,
            timestamp_field="generated_at",
            max_age_hours=max_age_hours,
            now=now,
            missing_reason=f"{slug} predictions missing",
            invalid_reason=f"{slug} predictions missing valid generated_at",
            stale_reason_prefix=f"{slug} predictions stale",
        )
        if age_hours is not None:
            prediction_ages.append(age_hours)

        surface_lines.append(
            _render_surface_line(
                slug=slug,
                surface="predictions",
                age_hours=age_hours,
                is_stale=is_stale,
                fallback_reason=reason,
            )
        )
        if is_stale:
            stale_prediction_models.append(slug)
            prediction_reasons.append(reason)

    for slug in sorted(accuracy_models):
        definition = accuracy_models[slug]

        per_show_row = _latest_timestamp_row(
            client,
            table=COMPLETED_SHOW_ACCURACY_TABLE,
            band=band,
            model_version=definition.version,
            timestamp_field="evaluated_at",
        )

        per_show_stale, per_show_age, per_show_reason = _evaluate_timestamp_row(
            row=per_show_row,
            timestamp_field="evaluated_at",
            max_age_hours=max_age_hours,
            now=now,
            missing_reason=f"{slug} per-show accuracy missing",
            invalid_reason=f"{slug} per-show accuracy missing valid evaluated_at",
            stale_reason_prefix=f"{slug} per-show accuracy stale",
        )

        if per_show_age is not None:
            accuracy_ages.append(per_show_age)

        is_stale = per_show_stale
        reasons = [per_show_reason] if per_show_reason else []
        surface_lines.append(
            _render_surface_line(
                slug=slug,
                surface="accuracy",
                age_hours=per_show_age,
                is_stale=is_stale,
                fallback_reason="; ".join(reasons) if reasons else "",
            )
        )
        if is_stale:
            stale_accuracy_models.append(slug)
            accuracy_reasons.extend(reasons)

    max_prediction_age_hours = max(prediction_ages) if prediction_ages else None
    max_accuracy_age_hours = max(accuracy_ages) if accuracy_ages else None

    if stale_prediction_models or (stale_accuracy_models and not skip_accuracy):
        freshness_state = "stale"
    elif stale_accuracy_models:
        freshness_state = "warning"
    elif prediction_models or accuracy_models:
        freshness_state = "fresh"
    else:
        freshness_state = "unknown"

    if freshness_state == "fresh":
        freshness_reason = (
            f"all supported model predictions and accuracy are within {max_age_hours}h"
        )
    elif freshness_state == "warning":
        joined = "; ".join(accuracy_reasons) or "supported-model accuracy stale"
        freshness_reason = (
            f"{joined}; tolerated because skip_accuracy=true for this run"
        )
    elif freshness_state == "stale":
        reasons = prediction_reasons[:]
        if not skip_accuracy:
            reasons.extend(accuracy_reasons)
        freshness_reason = "; ".join(reasons) or "supported-model freshness stale"
    else:
        freshness_reason = "no supported models resolved for freshness audit"

    if emit_text:
        print(
            f"[{band}] supported-model freshness state={freshness_state} "
            f"threshold={max_age_hours}h"
        )
        for line in surface_lines:
            print(line)
        print(
            "summary: "
            f"stale_prediction_models={','.join(stale_prediction_models) or 'none'} "
            f"stale_accuracy_models={','.join(stale_accuracy_models) or 'none'} "
            f"max_prediction_age_hours={_format_hours_output(max_prediction_age_hours) or 'n/a'} "
            f"max_accuracy_age_hours={_format_hours_output(max_accuracy_age_hours) or 'n/a'} "
            f"reason={freshness_reason}"
        )

    return SupportedModelFreshnessResult(
        band=band,
        max_age_hours=max_age_hours,
        skip_accuracy=skip_accuracy,
        freshness_state=freshness_state,
        stale_prediction_models=tuple(stale_prediction_models),
        stale_accuracy_models=tuple(stale_accuracy_models),
        max_prediction_age_hours=max_prediction_age_hours,
        max_accuracy_age_hours=max_accuracy_age_hours,
        freshness_reason=freshness_reason,
    )


def _render_surface_line(
    *,
    slug: str,
    surface: str,
    age_hours: float | None,
    is_stale: bool,
    fallback_reason: str,
) -> str:
    status = "stale" if is_stale else "fresh"
    if age_hours is not None:
        return f"- {slug} {surface}: {status} (age={age_hours:.1f}h)"
    if fallback_reason:
        return f"- {slug} {surface}: {status} ({fallback_reason})"
    return f"- {slug} {surface}: {status}"


def write_github_outputs(result: SupportedModelFreshnessResult) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return

    with open(github_output, "a", encoding="utf-8") as handle:
        for key, value in result.as_github_outputs().items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit supported-model prediction and accuracy freshness"
    )
    parser.add_argument("--band", required=True, help="Band slug to audit.")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=48,
        help="Maximum allowed supported-model staleness in hours.",
    )
    parser.add_argument(
        "--skip-accuracy",
        action="store_true",
        help="Treat stale accuracy as informational for this run.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Optional stdout format in addition to GitHub outputs.",
    )
    args = parser.parse_args()

    result = audit_supported_model_freshness(
        band=args.band,
        max_age_hours=args.max_age_hours,
        skip_accuracy=args.skip_accuracy,
        emit_text=args.format == "text",
    )
    write_github_outputs(result)

    if args.format == "json":
        print(json.dumps(result.as_dict()))


if __name__ == "__main__":
    main()
