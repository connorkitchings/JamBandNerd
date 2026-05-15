"""
Unified script to run a historical backtest for any band and model combination.

This script replaces the individual `backtest_<band>_<model>.py` files.
It iterates through historical shows, generates predictions for each, compares them
against the actual setlist, and saves the per-show accuracy metrics to the
`setlist_accuracy` table.

Usage:
  # Backtest the last 50 WSP shows with its active single-band model
  uv run python scripts/run_backtest.py --band wsp --shows 50

  # Backtest Goose over a specific date range
  uv run python scripts/run_backtest.py --band goose --start 2023-01-01 --end 2023-12-31
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta, timezone
from typing import Any

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import fetch_table, prepare_band_data
from src.jambandnerd.config import (
    SETLIST_ACCURACY_TABLE,
    SETLIST_RESULTS_TABLE,
)
from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.db.operations import (
    fetch_scored_show_ids,
    fetch_scored_target_show_keys,
    prune_setlist_corpus,
    upsert_dataframe,
    upsert_historical_prediction_run,
    upsert_setlist_accuracy_dataframe,
    upsert_setlist_result,
)
from src.jambandnerd.models.accuracy import (
    aggregate_metrics,
    compute_per_show_metrics,
    compute_weighted_precision_score,
    dual_objective_score_for_band,
)
from src.jambandnerd.models.evaluation import (
    get_evaluation_reference_date,
    list_completed_shows,
    select_target_shows,
)
from src.jambandnerd.models.model_test_cache import LocalModelTestCache
from src.jambandnerd.models.registry import (
    build_band_predictor,
    build_predictor,
    get_band_metadata,
    get_band_serializer,
    get_model_definition,
    list_backtest_models,
    serialize_model_predictions,
)
from src.jambandnerd.transformations.gaps import generate_model_data


def _write_github_output(key: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def load_backtest_frames(
    band: str,
    *,
    snapshot_root: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and prepare the raw inputs required for a historical backtest."""

    if snapshot_root:
        shows_rows = fetch_table(f"{band}_shows_raw", snapshot_root=snapshot_root)
        setlist_rows = fetch_table(f"{band}_setlists_raw", snapshot_root=snapshot_root)
    else:
        shows_rows = fetch_table(f"{band}_shows_raw")
        setlist_rows = fetch_table(f"{band}_setlists_raw")

    shows_df = pd.DataFrame(shows_rows)
    sets_df = pd.DataFrame(setlist_rows)
    if shows_df.empty or sets_df.empty:
        return shows_df, sets_df
    return prepare_band_data(shows_df, sets_df, band=band)


def build_scored_run_records(
    *,
    band: str,
    model: str | None,
    shows_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    target_shows: pd.DataFrame,
    exclusion_window: int | None,
    local_cache: LocalModelTestCache | None = None,
    show_progress: bool = False,
) -> list[dict[str, Any]]:
    """Build detailed per-show scored-run records without writing to Supabase."""

    if model is None:
        band_metadata = get_band_metadata(band)
        predictor = build_band_predictor(band, persist_artifacts=False)
        model_version = band_metadata.model_version
        serializer = get_band_serializer(band)
        top_k = band_metadata.default_top_k
        model_label = model_version
        supports_training = True
    else:
        definition = get_model_definition(model)
        kwargs: dict[str, Any] = {}
        if definition.supports_training:
            kwargs["persist_artifacts"] = False
        predictor = build_predictor(model, band=band, **kwargs)
        model_version = definition.version

        def serializer(preds):
            return serialize_model_predictions(model, preds)

        top_k = definition.default_top_k
        model_label = model.upper()
        supports_training = definition.supports_training
    scored_run_records: list[dict[str, Any]] = []
    total_shows = len(target_shows)

    for index, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        ref_date = show_row["show_date"]
        show_id = str(show_row["show_id"])
        if show_progress:
            target_date = (
                ref_date.isoformat() if isinstance(ref_date, date) else ref_date
            )
            print(
                f"[{band.upper()}/{model_label}] Scoring retained show "
                f"{index}/{total_shows}: target_show_date={target_date} "
                f"show_id={show_id}",
                flush=True,
            )

        if not isinstance(ref_date, date):
            continue

        actual_songs = (
            sets_df.loc[sets_df["show_id"] == show_id, "song_name"]
            .dropna()
            .unique()
            .tolist()
        )
        if not actual_songs or len(actual_songs) <= 2:
            continue

        prediction_date = get_evaluation_reference_date(ref_date)
        if local_cache is not None:
            cached = local_cache.load_scored_run(
                band=band,
                model_slug=model or band,
                reference_date=prediction_date.isoformat(),
                target_show_id=show_id,
            )
            if cached is not None:
                scored_run_records.append(cached)
                continue

        try:
            model_data = generate_model_data(
                shows_df,
                sets_df,
                prediction_date,
                exclusion_window=exclusion_window,
                band=band,
                target_show_context=show_row,
            )

            if supports_training:
                predictor.train(model_data)
            prediction_output = predictor.predict(
                model_data=model_data,
                top_k=top_k,
            )
            preds = (
                prediction_output[0]
                if isinstance(prediction_output, tuple)
                else prediction_output
            )

            if not preds:
                continue

            serialized_predictions = serializer(preds)
            pred_songs = [
                prediction["song_name"] for prediction in serialized_predictions
            ]
        except (ValueError, AttributeError, KeyError, TypeError):
            continue
        except Exception:
            continue

        metrics_by_k: dict[str, dict[str, float]] = {}
        for k in [10, 25, 50]:
            metrics_by_k[f"k{k}"] = compute_per_show_metrics(
                pred_songs,
                actual_songs,
                k,
            )

        record = {
            "band": band,
            "model_slug": model,
            "model_version": model_version,
            "show_id": show_id,
            "target_show_date": ref_date.isoformat(),
            "reference_date": prediction_date.isoformat(),
            "actual_songs": actual_songs,
            "actual_song_count": len(actual_songs),
            "predictions": serialized_predictions,
            "prediction_count": len(serialized_predictions),
            "generated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
            "metrics": metrics_by_k,
        }
        if local_cache is not None:
            local_cache.write_scored_run(record)
        scored_run_records.append(record)

    return scored_run_records


def build_accuracy_results_dataframe(
    scored_run_records: list[dict[str, Any]],
    *,
    prediction_run_ids: dict[tuple[str, str], int],
) -> pd.DataFrame:
    """Build the setlist_accuracy payload from detailed scored-run records."""

    rows: list[dict[str, Any]] = []
    for record in scored_run_records:
        key = (str(record["reference_date"]), str(record["show_id"]))
        prediction_run_id = prediction_run_ids.get(key)
        if prediction_run_id is None:
            raise RuntimeError(f"Missing prediction run id for scored run {key}")

        row = {
            "band": record["band"],
            "model_version": record["model_version"],
            "show_id": record["show_id"],
            "target_show_key": record["show_id"],
            "show_date": record["target_show_date"],
            "target_show_date": record["target_show_date"],
            "reference_date": record["reference_date"],
            "actual_song_count": record["actual_song_count"],
            "prediction_run_id": prediction_run_id,
            "evaluated_at": record["generated_at"],
        }
        precision_by_k: dict[int, float] = {}
        for k in [10, 25, 50]:
            metrics = record["metrics"][f"k{k}"]
            precision_by_k[k] = metrics["precision"]
            row[f"p{k}"] = metrics["precision"]
            row[f"recall_{k}"] = metrics["recall"]
        row["weighted_precision_score"] = compute_weighted_precision_score(
            precision_by_k[10], precision_by_k[25], precision_by_k[50]
        )
        rows.append(row)

    return pd.DataFrame(rows)


def persist_scored_run_records(
    scored_run_records: list[dict[str, Any]],
    *,
    historical_runs_table: str = SETLIST_RESULTS_TABLE,
    accuracy_table: str = SETLIST_ACCURACY_TABLE,
    legacy_lineage: bool = False,
) -> pd.DataFrame:
    """Persist detailed scored-run records to replay lineage and per-show tables."""

    if not scored_run_records:
        return pd.DataFrame()

    prediction_run_ids: dict[tuple[str, str], int] = {}
    for record in scored_run_records:
        if legacy_lineage:
            run_id = upsert_historical_prediction_run(
                band=str(record["band"]),
                model_slug=str(record["model_slug"]),
                model_version=str(record["model_version"]),
                reference_date=str(record["reference_date"]),
                target_show_id=str(record["show_id"]),
                target_show_date=str(record["target_show_date"]),
                generated_at=str(record["generated_at"]),
                predictions=list(record["predictions"]),
                actual_songs=list(record["actual_songs"]),
                table_name=historical_runs_table,
            )
        else:
            run_id = upsert_setlist_result(
                band=str(record["band"]),
                model_version=str(record["model_version"]),
                target_show_key=str(record["show_id"]),
                target_show_date=str(record["target_show_date"]),
                reference_date=str(record["reference_date"]),
                generated_at=str(record["generated_at"]),
                predictions=list(record["predictions"]),
                actual_songs=list(record["actual_songs"]),
                table_name=historical_runs_table,
            )
        prediction_run_ids[(str(record["reference_date"]), str(record["show_id"]))] = (
            run_id
        )

    results_df = build_accuracy_results_dataframe(
        scored_run_records,
        prediction_run_ids=prediction_run_ids,
    )
    if results_df.empty:
        return results_df

    if accuracy_table == SETLIST_ACCURACY_TABLE:
        upsert_setlist_accuracy_dataframe(results_df, table_name=accuracy_table)
    else:
        upsert_dataframe(
            table_name=accuracy_table,
            df=results_df,
            conflict_columns=["band", "model_version", "target_show_key"],
        )
    return results_df


def build_prediction_rows_dataframe(
    scored_run_records: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build canonical prediction rows deduped by reference_date."""

    if not scored_run_records:
        return pd.DataFrame()

    rows_by_reference_date: dict[str, dict[str, Any]] = {}
    for record in scored_run_records:
        rows_by_reference_date[str(record["reference_date"])] = {
            "band": record["band"],
            "reference_date": record["reference_date"],
            "model_version": record["model_version"],
            "top_k": record["prediction_count"],
            "predictions": record["predictions"],
            "predicted_at": record["generated_at"],
        }

    return pd.DataFrame(
        [rows_by_reference_date[key] for key in sorted(rows_by_reference_date)]
    )


def summarize_scored_run_records(
    scored_run_records: list[dict[str, Any]],
) -> dict[int, dict[str, float]]:
    """Aggregate scored-run records into K-based summary metrics."""

    summaries: dict[int, dict[str, float]] = {}
    for k in [10, 25, 50]:
        agg_metrics_k = aggregate_metrics(
            [record["metrics"][f"k{k}"] for record in scored_run_records],
            k,
        )
        summaries[k] = {
            "hit_rate": agg_metrics_k.hit_rate,
            "avg_matches": agg_metrics_k.avg_matches,
            "precision": agg_metrics_k.precision,
            "recall": agg_metrics_k.recall,
            "f1": agg_metrics_k.f1,
            "ndcg": agg_metrics_k.ndcg,
        }
    return summaries


def run_backtest(
    band: str,
    model: str | None,
    start: str | None,
    end: str | None,
    shows: int | None,
    exclusion_window: int | None,
    all_history: bool = False,
    incremental: bool = True,
    snapshot_root: str | None = None,
    require_results: bool = False,
    prune_to_window: bool = True,
    dry_run: bool = False,
) -> int:
    """Run a backtest for a given band and model.

    When ``incremental=True`` (the default), shows that already have a scored
    row in ``setlist_accuracy`` for this band/model_version are skipped.
    This means a typical daily run scores only the 0-2 new shows that occurred
    since the last run rather than recomputing the entire window.

    Use ``incremental=False`` (or ``--all-history``) to force a full recompute,
    e.g. after a model version bump or a data correction.
    """
    model_context = (
        get_band_metadata(band) if model is None else get_model_definition(model)
    )
    model_version = (
        model_context.model_version if model is None else model_context.version
    )
    log_prefix = f"[{band.upper()}/{model_version}]"

    # 1. Fetch and prepare data
    print(f"{log_prefix} Fetching raw data...")
    shows_df, sets_df = load_backtest_frames(band, snapshot_root=snapshot_root)

    if shows_df.empty or sets_df.empty:
        message = f"{log_prefix} No data to backtest. Aborting."
        print(message)
        if require_results:
            raise RuntimeError(message)
        return 0

    # 2. Determine target shows for backtesting
    completed_shows = list_completed_shows(shows_df, sets_df)

    if all_history:
        target_shows = select_target_shows(completed_shows, all_history=True)
        window_start = target_shows["show_date"].min()
        window_end = target_shows["show_date"].max()
        print(
            f"{log_prefix} Backtesting across full completed-show history: {len(target_shows)} shows from {window_start} to {window_end}"
        )
    elif shows and shows > 0:
        target_shows = select_target_shows(completed_shows, shows=shows)
        window_start = target_shows["show_date"].min()
        window_end = target_shows["show_date"].max()
        print(
            f"{log_prefix} Backtesting on last {len(target_shows)} completed shows from {window_start} to {window_end}"
        )
    else:
        start_d = (
            pd.to_datetime(start).date()
            if start
            else (date.today() - timedelta(days=365 * 10))
        )
        end_d = pd.to_datetime(end).date() if end else date.today()
        target_shows = select_target_shows(completed_shows, start=start, end=end)
        print(
            f"{log_prefix} Backtesting on {len(target_shows)} completed shows from {start_d} to {end_d}"
        )

    if target_shows.empty:
        message = f"{log_prefix} No shows found in the specified window."
        print(message)
        if require_results:
            raise RuntimeError(message)
        return 0
    retained_window_keys = target_shows["show_id"].astype(str).tolist()

    # 3. Score target shows and persist results
    supports_backtest = True if model is None else model_context.supports_backtest
    supports_training = True if model is None else model_context.supports_training

    # 2b. Incremental filter: skip shows already present in setlist_accuracy.
    # This is applied after the window is selected and the empty-window check,
    # so data-loading failures still raise under --require-results.
    # "All already scored" is a valid steady state and does NOT raise.
    if incremental and not all_history:
        candidate_ids = set(target_shows["show_id"].astype(str))
        if model is None:
            already_scored = fetch_scored_target_show_keys(
                band,
                model_version,
                candidate_target_show_keys=candidate_ids,
                table_name=SETLIST_ACCURACY_TABLE,
            )
        else:
            already_scored = fetch_scored_show_ids(
                band,
                model_version,
                candidate_show_ids=candidate_ids,
                table_name=SETLIST_ACCURACY_TABLE,
            )
        new_ids = candidate_ids - already_scored
        skipped = len(candidate_ids) - len(new_ids)
        if skipped:
            print(
                f"{log_prefix} Incremental: {skipped} show(s) already scored, {len(new_ids)} new."
            )
        if not new_ids:
            print(f"{log_prefix} All shows in window already scored. Nothing to do.")
            if prune_to_window and not dry_run:
                deleted = prune_setlist_corpus(
                    band=band,
                    model_version=model_version,
                    retained_target_show_keys=retained_window_keys,
                    results_table=SETLIST_RESULTS_TABLE,
                    accuracy_table=SETLIST_ACCURACY_TABLE,
                )
                if deleted:
                    print(
                        f"{log_prefix} Pruned {deleted} completed-show row(s) outside retained window."
                    )
            return 0
        target_shows = target_shows[target_shows["show_id"].astype(str).isin(new_ids)]

    _write_github_output("backtest_incremental_all_scored", "false")

    if not supports_backtest:
        raise ValueError(f"Model does not support backtests: {model}")
    if supports_training:
        print(
            f"{log_prefix} Historical scoring uses in-memory fresh training; cached model artifacts are disabled."
        )
    scored_run_records = build_scored_run_records(
        band=band,
        model=model,
        shows_df=shows_df,
        sets_df=sets_df,
        target_shows=target_shows,
        exclusion_window=exclusion_window,
        show_progress=True,
    )

    # 5. Save results and print summary
    if scored_run_records:
        results_df = pd.DataFrame()
        if dry_run:
            print(
                f"{log_prefix} Dry run: scored {len(scored_run_records)} "
                "completed-show record(s); no Supabase writes or pruning performed."
            )
        else:
            results_df = persist_scored_run_records(
                scored_run_records,
                historical_runs_table=SETLIST_RESULTS_TABLE,
                accuracy_table=SETLIST_ACCURACY_TABLE,
            )
        if prune_to_window and not dry_run:
            deleted = prune_setlist_corpus(
                band=band,
                model_version=model_version,
                retained_target_show_keys=retained_window_keys,
                results_table=SETLIST_RESULTS_TABLE,
                accuracy_table=SETLIST_ACCURACY_TABLE,
            )
            if deleted:
                print(
                    f"{log_prefix} Pruned {deleted} completed-show row(s) outside retained window."
                )
        if not dry_run:
            print(
                f"{log_prefix} Saving {len(results_df)} per-show accuracy records to the database..."
            )
            print(f"{log_prefix} Save complete.")

        print(f"\n{log_prefix} --- Aggregate Metrics for Window ---")
        summary = summarize_scored_run_records(scored_run_records)
        for k in [10, 25, 50]:
            agg_metrics_k = summary[k]
            print(
                f"{log_prefix} K={k}: hit_rate={agg_metrics_k['hit_rate']:.3f} avg_matches={agg_metrics_k['avg_matches']:.3f} "
                f"precision={agg_metrics_k['precision']:.3f} recall={agg_metrics_k['recall']:.3f} f1={agg_metrics_k['f1']:.3f}"
            )
        p10 = summary[10]["precision"]
        r50 = summary[50]["recall"]
        weighted = compute_weighted_precision_score(
            summary[10]["precision"], summary[25]["precision"], summary[50]["precision"]
        )
        dual = dual_objective_score_for_band(p10, r50, band)
        print(
            f"\n{log_prefix} DUAL OBJECTIVE | {band} | "
            f"p@10={p10:.3f} | r@50={r50:.3f} | "
            f"dual={dual:.3f} | weighted_p={weighted:.3f} | n={len(scored_run_records)}"
        )
        return len(scored_run_records)
    else:
        message = f"{log_prefix} No results generated from backtest."
        print(message)
        if require_results:
            raise RuntimeError(message)
        return 0


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run a historical backtest for a specific band and model."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        choices=get_repo_supported_bands(),
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=False,
        choices=[definition.slug for definition in list_backtest_models()],
        help="Legacy model slug to backtest. Omit for the active single-band model.",
    )
    parser.add_argument("--start", help="Start date for backtest window (YYYY-MM-DD).")
    parser.add_argument("--end", help="End date for backtest window (YYYY-MM-DD).")
    parser.add_argument(
        "--shows",
        type=int,
        help="Limit to the last N completed shows (overrides start/end).",
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=None,
        help="Number of recent shows to exclude songs from. Defaults to band-specific config.",
    )
    parser.add_argument(
        "--all-history",
        action="store_true",
        help="Backtest across all completed shows, ignoring --shows and date window arguments.",
    )
    parser.add_argument(
        "--snapshot-root",
        help="Optional local snapshot directory for raw table reads.",
    )
    parser.add_argument(
        "--require-results",
        action="store_true",
        help="Exit non-zero if the run would otherwise finish without writing scored results.",
    )
    parser.add_argument(
        "--incremental",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Skip shows already present in setlist_accuracy for this band/model "
            "(default: on). Use --no-incremental to force a full recompute."
        ),
    )
    parser.add_argument(
        "--prune-to-window",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Hard-delete completed-show rows outside the selected retained window.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score the selected window and print metrics without writing tables.",
    )
    args = parser.parse_args()

    run_backtest(
        band=args.band,
        model=args.model,
        start=args.start,
        end=args.end,
        shows=args.shows,
        exclusion_window=args.exclusion_window,
        all_history=args.all_history,
        incremental=args.incremental,
        snapshot_root=args.snapshot_root,
        require_results=args.require_results,
        prune_to_window=args.prune_to_window,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
