"""Apply the promotion gate to two BacktestSummary files and print the decision.

This script does NOT mutate the registry or metadata — promotion is a
deliberate PR-level edit.  Run this after run_phase_b_backtest.py produces
summary JSON files for both the incumbent and the candidate.

Usage:
  uv run python scripts/promote_phase_b_winner.py \\
      --incumbent backtests/goose_goose_phase_b_v1_summary.json \\
      --candidate  backtests/goose_goose_phase_b_v2_logistic_summary.json

Exit codes:
  0  — candidate is promotion-eligible
  1  — candidate is NOT eligible (blockers printed)
"""

from __future__ import annotations

import argparse
import json

# Make sure project root is on path when run directly
import os
import sys
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.models.accuracy import BacktestSummary
from src.jambandnerd.models.readiness import is_band_promotion_eligible


def _load_summary(path: str) -> BacktestSummary:
    data = json.loads(Path(path).read_text())
    return BacktestSummary(**data)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply the Phase B promotion gate to two BacktestSummary files."
    )
    parser.add_argument(
        "--incumbent",
        required=True,
        help="Path to the incumbent model's BacktestSummary JSON.",
    )
    parser.add_argument(
        "--candidate",
        required=True,
        help="Path to the candidate model's BacktestSummary JSON.",
    )
    parser.add_argument(
        "--min-p10-delta",
        type=float,
        default=0.02,
        help="Minimum absolute p@10 improvement required (default: 0.02).",
    )
    parser.add_argument(
        "--min-r50-delta",
        type=float,
        default=0.02,
        help="Minimum absolute r@50 improvement required (default: 0.02).",
    )
    parser.add_argument(
        "--min-shows",
        type=int,
        default=100,
        help="Minimum show count for a valid comparison (default: 100).",
    )
    args = parser.parse_args()

    incumbent = _load_summary(args.incumbent)
    candidate = _load_summary(args.candidate)

    decision = is_band_promotion_eligible(
        candidate=candidate,
        incumbent=incumbent,
        min_p10_delta=args.min_p10_delta,
        min_r50_delta=args.min_r50_delta,
        min_shows=args.min_shows,
    )

    print("\n=== Phase B Promotion Decision ===")
    print(f"  Band:              {incumbent.band}")
    print(f"  Incumbent:         {decision.incumbent_version} (n={incumbent.n_shows})")
    print(f"  Candidate:         {decision.candidate_version} (n={candidate.n_shows})")
    print(
        f"  Δp@10:             {decision.p10_delta:+.4f}  (threshold: +{args.min_p10_delta:.4f})"
    )
    print(
        f"  Δr@50:             {decision.r50_delta:+.4f}  (threshold: +{args.min_r50_delta:.4f})"
    )
    print(f"  Incumbent dual:    {incumbent.dual_score:.4f}")
    print(f"  Candidate dual:    {candidate.dual_score:.4f}")
    print(f"  Δdual:             {candidate.dual_score - incumbent.dual_score:+.4f}")

    if decision.eligible:
        print("\n  ✓ ELIGIBLE — candidate clears the promotion gate.")
        print(
            "\n  Next step: update src/jambandnerd/models/metadata.py and "
            "(if GBM wins) registry.py, then run npm run verify:python."
        )
        sys.exit(0)
    else:
        print("\n  ✗ NOT ELIGIBLE — blockers:")
        for blocker in decision.blockers:
            print(f"    · {blocker}")
        sys.exit(1)


if __name__ == "__main__":
    main()
