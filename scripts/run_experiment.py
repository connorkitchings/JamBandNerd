"""Band-agnostic experiment sweep runner.

Usage:
  uv run python scripts/run_experiment.py --band goose --sweep hp_sweep
  uv run python scripts/run_experiment.py --band goose --sweep hp_sweep --only hp_leaves63_r400
  uv run python scripts/run_experiment.py --band goose --sweep hp_sweep --shows 50
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.models.base import PredictionModel
from jambandnerd.models.experiment import (
    ExperimentConfig,
    SweepResult,
    make_experiment_predictor,
)
from scripts.run_phase_b_backtest import run_phase_b_backtest

# Per-band base predictor class for HP sweeps.
_BASE_PREDICTOR_PATHS: dict[str, str] = {
    "goose": "jambandnerd.models.goose.fast_predictor.GooseFastPredictor",
}


def _import_class(dotted_path: str) -> type[PredictionModel]:
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, PredictionModel)):
        raise TypeError(f"{dotted_path} must be a PredictionModel subclass")
    return cls


def _load_sweeps(band: str) -> dict[str, list[ExperimentConfig]]:
    module = importlib.import_module(
        f"jambandnerd.models.{band}.experiments"
    )
    sweeps: dict[str, list[ExperimentConfig]] = getattr(
        module, f"{band.upper()}_SWEEPS", {}
    )
    if not sweeps:
        raise ValueError(f"No sweeps defined for band '{band}'.")
    return sweeps


def run_experiment(
    *,
    config: ExperimentConfig,
    band: str,
    shows: int,
    snapshot_root: str | None,
    out_dir: str,
) -> SweepResult:
    if config.predictor_path:
        predictor_cls = _import_class(config.predictor_path)
    else:
        base_path = config.base_predictor_path or _BASE_PREDICTOR_PATHS.get(band, "")
        if not base_path:
            raise ValueError(f"No base predictor path for band '{band}'.")

        base_cls = _import_class(base_path)
        predictor_cls = make_experiment_predictor(
            base_cls,
            slug_suffix=config.slug,
            param_overrides=config.param_overrides or None,
            round_overrides=config.round_overrides,
            feature_cols=config.feature_cols,
        )

    t0 = time.perf_counter()
    summary = run_phase_b_backtest(
        band=band,
        predictor_class=predictor_cls,
        shows=shows,
        snapshot_root=snapshot_root,
        out_dir=out_dir,
    )
    elapsed = time.perf_counter() - t0

    return SweepResult(
        slug=config.slug,
        model_version=predictor_cls.MODEL_VERSION,
        dual_score=summary.dual_score,
        p10=summary.p10,
        p25=summary.p25,
        r50=summary.r50,
        f1_25=summary.f1_25,
        dual_f1_score=summary.dual_f1_score,
        n_shows=summary.n_shows,
        summary_path=str(Path(out_dir) / f"{band}_{predictor_cls.MODEL_VERSION}_summary.json"),
        elapsed_s=elapsed,
    )


def _print_results_table(results: list[SweepResult], baseline_dual: float | None = None) -> None:
    header = f"{'Experiment':<28} {'dual':>7} {'p@10':>7} {'p@25':>7} {'r@50':>7} {'F1@25':>7} {'dual_f1':>7} {'n':>4} {'time':>7}"
    sep = "-" * len(header)
    print(f"\n{sep}")
    print(header)
    print(sep)
    for r in results:
        marker = ""
        if baseline_dual is not None:
            delta = r.dual_score - baseline_dual
            if delta > 0:
                marker = f"  +{delta:.4f}"
            elif delta < 0:
                marker = f"  {delta:.4f}"
        print(
            f"{r.slug:<28} {r.dual_score:7.4f} {r.p10:7.4f} {r.p25:7.4f} "
            f"{r.r50:7.4f} {r.f1_25:7.4f} {r.dual_f1_score:7.4f} {r.n_shows:4d} "
            f"{r.elapsed_s:6.0f}s{marker}"
        )
    print(sep)

    if results:
        best = max(results, key=lambda r: r.dual_score)
        print(f"\nBest: {best.slug} (dual={best.dual_score:.4f})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Band-agnostic experiment sweep runner."
    )
    parser.add_argument("--band", required=True, help="Band identifier (goose, …)")
    parser.add_argument(
        "--sweep",
        required=True,
        help="Sweep name as defined in the band's experiments module.",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Run a single experiment slug from the sweep.",
    )
    parser.add_argument(
        "--shows",
        type=int,
        default=100,
        help="Number of recent shows to score (default: 100).",
    )
    parser.add_argument(
        "--snapshot-root",
        default=".snapshots/goose_phase_b",
        help="Local snapshot directory.",
    )
    parser.add_argument(
        "--out-dir",
        default="backtests",
        help="Output directory for result files.",
    )
    args = parser.parse_args()

    sweeps = _load_sweeps(args.band)
    if args.sweep not in sweeps:
        available = ", ".join(sweeps.keys())
        raise SystemExit(
            f"Unknown sweep '{args.sweep}' for band '{args.band}'. "
            f"Available: {available}"
        )

    experiments = sweeps[args.sweep]
    if args.only:
        experiments = [c for c in experiments if c.slug == args.only]
        if not experiments:
            slugs = ", ".join(c.slug for c in sweeps[args.sweep])
            raise SystemExit(
                f"Experiment '{args.only}' not found in sweep '{args.sweep}'. "
                f"Available: {slugs}"
            )

    results: list[SweepResult] = []
    for i, config in enumerate(experiments, start=1):
        print(f"\n[{i}/{len(experiments)}] {config.slug}: {config.description}")
        try:
            result = run_experiment(
                config=config,
                band=args.band,
                shows=args.shows,
                snapshot_root=args.snapshot_root,
                out_dir=args.out_dir,
            )
            results.append(result)
        except Exception as exc:
            print(f"  FAILED: {exc}")

    if results:
        _print_results_table(results)
    else:
        print("\nNo experiments completed successfully.")


if __name__ == "__main__":
    main()
