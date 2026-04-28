"""Sync the active retained completed-show prediction corpus."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.run_backtest import run_backtest
from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.models.registry import list_pipeline_models


def _selected_pipeline_models(models: Sequence[str] | None = None):
    definitions = list_pipeline_models()
    if not models:
        return definitions

    by_slug = {definition.slug: definition for definition in definitions}
    unknown = [model for model in models if model not in by_slug]
    if unknown:
        raise ValueError(
            "Unsupported retained-corpus model(s): " + ", ".join(sorted(unknown))
        )

    selected: list[object] = []
    seen: set[str] = set()
    for model in models:
        if model in seen:
            continue
        seen.add(model)
        selected.append(by_slug[model])
    return selected


def sync_retained_prediction_corpus(
    *,
    band: str,
    window: int = 50,
    incremental: bool = True,
    require_results: bool = False,
    dry_run: bool = False,
    models: Sequence[str] | None = None,
) -> int:
    """Score and prune the last-N completed-show corpus for all promoted models."""
    total_scored = 0
    for definition in _selected_pipeline_models(models):
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
            dry_run=dry_run,
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
        "--model",
        dest="models",
        action="append",
        choices=[definition.slug for definition in list_pipeline_models()],
        help="Promoted model to sync (repeat for multiple). Defaults to all promoted models.",
    )
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
        help="Score promoted models without writing retained tables.",
    )
    args = parser.parse_args()

    sync_retained_prediction_corpus(
        band=args.band,
        window=args.window,
        incremental=args.incremental,
        require_results=args.require_results,
        dry_run=args.dry_run,
        models=args.models,
    )


if __name__ == "__main__":
    main()
