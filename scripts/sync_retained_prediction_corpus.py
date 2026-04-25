"""Sync the active retained completed-show prediction corpus."""

from __future__ import annotations

import argparse
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.run_backtest import run_backtest
from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.models.registry import list_pipeline_models


def sync_retained_prediction_corpus(
    *,
    band: str,
    window: int = 50,
    incremental: bool = True,
    require_results: bool = False,
) -> int:
    """Score and prune the last-N completed-show corpus for all promoted models."""
    total_scored = 0
    for definition in list_pipeline_models():
        scored = run_backtest(
            band=band,
            model=definition.slug,
            start=None,
            end=None,
            shows=window,
            exclusion_window=None,
            incremental=incremental,
            require_results=require_results,
            prune_to_window=True,
        )
        total_scored += scored
    return total_scored


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync retained completed-show prediction and accuracy corpus."
    )
    parser.add_argument("--band", required=True, choices=get_repo_supported_bands())
    parser.add_argument("--window", type=int, default=50)
    parser.add_argument(
        "--incremental",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip already-scored completed shows when possible.",
    )
    parser.add_argument(
        "--require-results",
        action="store_true",
        help="Exit non-zero when no new retained rows are written.",
    )
    args = parser.parse_args()

    sync_retained_prediction_corpus(
        band=args.band,
        window=args.window,
        incremental=args.incremental,
        require_results=args.require_results,
    )


if __name__ == "__main__":
    main()
