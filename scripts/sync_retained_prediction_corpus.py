"""Sync the active retained completed-show prediction corpus."""

from __future__ import annotations

import argparse
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.run_backtest import run_backtest
from src.jambandnerd.models.registry import list_active_bands


def sync_retained_prediction_corpus(
    *,
    band: str,
    window: int = 100,
    incremental: bool = True,
    require_results: bool = False,
    dry_run: bool = False,
) -> int:
    """Score and prune the last-N completed-show corpus for a band's active model."""
    return run_backtest(
        band=band,
        model=None,
        start=None,
        end=None,
        shows=window,
        exclusion_window=None,
        incremental=incremental,
        require_results=require_results,
        prune_to_window=True,
        dry_run=dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync retained completed-show prediction and accuracy corpus."
    )
    parser.add_argument("--band", required=True, choices=list_active_bands())
    parser.add_argument("--window", type=int, default=100)
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score the band's registered model without writing retained tables.",
    )
    args = parser.parse_args()

    sync_retained_prediction_corpus(
        band=args.band,
        window=args.window,
        incremental=args.incremental,
        require_results=args.require_results,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
