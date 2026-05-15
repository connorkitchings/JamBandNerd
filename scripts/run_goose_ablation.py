from __future__ import annotations

import json
import os
import sys
import time
from functools import partial
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.models.goose.ablation import GooseFastAblationPredictor
from scripts.run_phase_b_backtest import run_phase_b_backtest

BAND = "goose"
SNAPSHOT = ".snapshots/goose_phase_b"

CORE = [
    "current_gap",
    "plays_past_year",
    "plays_past_50",
    "career_play_pct",
]

ABLATION_VARIANTS: list[tuple[str, list[str]]] = [
    ("core", CORE),
    ("+month", CORE + ["month_play_rate"]),
    ("+overdue", CORE + ["overdue_ratio"]),
    ("+ltp_recent", CORE + ["avg_ltp_recent", "ltp_diff_recent"]),
    ("+hot3", CORE + ["plays_past_3", "plays_past_5"]),
    ("+plays10", CORE + ["plays_past_10"]),
    ("+plays25", CORE + ["plays_past_25", "diff_25_to_50"]),
    ("+tour", CORE + ["tour_position", "show_position_in_run"]),
    ("+venue", CORE + ["same_venue_run_position"]),
    (
        "full_v1_plus_ppl",
        [
            "current_gap",
            "plays_past_3",
            "plays_past_5",
            "plays_past_10",
            "plays_past_25",
            "plays_past_50",
            "career_play_pct",
            "month_play_rate",
            "diff_25_to_50",
            "show_position_in_run",
            "tour_position",
            "same_venue_run_position",
            "overdue_ratio",
            "avg_ltp_recent",
            "ltp_diff_recent",
            "plays_past_year",
        ],
    ),
]


def main() -> None:
    results: list[dict] = []
    total = len(ABLATION_VARIANTS)

    for i, (name, features) in enumerate(ABLATION_VARIANTS, 1):
        label = f"goose_ablation_{name}"
        print(f"\n[{i}/{total}] {label} ({len(features)} features)")
        t0 = time.perf_counter()
        try:
            predictor_factory = partial(
                GooseFastAblationPredictor,
                feature_cols=features,
                variant_name=name,
            )
            summary = run_phase_b_backtest(
                band=BAND,
                predictor_class=predictor_factory,
                shows=100,
                snapshot_root=SNAPSHOT,
                out_dir="backtests/",
            )
            elapsed = time.perf_counter() - t0
            results.append(
                {
                    "variant": name,
                    "n_features": len(features),
                    "features": features,
                    "dual": round(summary.dual_score, 4),
                    "p10": round(summary.p10, 4),
                    "r50": round(summary.r50, 4),
                    "n_shows": summary.n_shows,
                    "elapsed_s": round(elapsed, 1),
                }
            )
            print(
                f"  -> dual={summary.dual_score:.4f} "
                f"p@10={summary.p10:.3f} r@50={summary.r50:.3f} "
                f"({elapsed:.1f}s)"
            )
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"  -> ERROR: {exc} ({elapsed:.1f}s)")
            results.append(
                {
                    "variant": name,
                    "n_features": len(features),
                    "features": features,
                    "error": str(exc),
                    "elapsed_s": round(elapsed, 1),
                }
            )

    out_path = Path("backtests/goose_feature_ablation_results.json")
    out_path.write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 72)
    print("GOOSE FEATURE ABLATION RESULTS")
    print("=" * 72)
    print(f"{'variant':<22} {'#feat':>4} {'dual':>8} {'p@10':>8} {'r@50':>8}")
    print("-" * 52)
    for r in sorted(results, key=lambda x: x.get("dual", 0), reverse=True):
        if "dual" in r:
            print(
                f"{r['variant']:<22} {r['n_features']:>4} "
                f"{r['dual']:>8.4f} {r['p10']:>8.4f} {r['r50']:>8.4f}"
            )
        else:
            print(f"{r['variant']:<22} {r['n_features']:>4}   ERROR: {r['error'][:40]}")

    print(
        "\nBaseline: Notebook 1yr = 0.408, GooseFast v1 = 0.378, "
        "Goose phase_b v1 (logistic) = 0.399"
    )
    print(f"Full results: {out_path}")


if __name__ == "__main__":
    main()
