"""Run notebook window ablation backtests across all bands.

Usage:
    uv run python scripts/run_notebook_ablation.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.models.notebook.ablation import (
    Notebook1yrPredictor,
    Notebook2yrPredictor,
    Notebook50Predictor,
    Notebook100Predictor,
)
from scripts.run_phase_b_backtest import run_phase_b_backtest

BANDS = [
    ("goose", ".snapshots/goose_phase_b"),
    ("billy", ".snapshots/billy_phase_b"),
    ("wsp", ".snapshots/wsp"),
    ("phish", ".snapshots/phish_phase_b"),
    ("um", ".snapshots/um_phase_b"),
]

VARIANTS = [
    ("1yr", Notebook1yrPredictor),
    ("2yr", Notebook2yrPredictor),
    ("50", Notebook50Predictor),
    ("100", Notebook100Predictor),
]


def main() -> None:
    results: list[dict] = []
    total = len(BANDS) * len(VARIANTS)
    i = 0

    for band, snapshot_root in BANDS:
        for variant_name, predictor_class in VARIANTS:
            i += 1
            label = f"{band}/notebook_{variant_name}"
            print(f"\n[{i}/{total}] {label}")
            t0 = time.perf_counter()
            try:
                summary = run_phase_b_backtest(
                    band=band,
                    predictor_class=predictor_class,
                    shows=100,
                    snapshot_root=snapshot_root,
                    out_dir="backtests/",
                )
                elapsed = time.perf_counter() - t0
                results.append(
                    {
                        "band": band,
                        "variant": variant_name,
                        "dual": round(summary.dual_score, 4),
                        "p10": round(summary.p10, 4),
                        "r50": round(summary.r50, 4),
                        "dual_f1": round(summary.dual_f1_score, 4),
                        "weighted": round(summary.weighted_score, 4),
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
                        "band": band,
                        "variant": variant_name,
                        "error": str(exc),
                        "elapsed_s": round(elapsed, 1),
                    }
                )

    out_path = Path("backtests/notebook_ablation_results.json")
    out_path.write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 72)
    print("NOTEBOOK WINDOW ABLATION RESULTS")
    print("=" * 72)

    bands_seen = sorted(set(r["band"] for r in results if "dual" in r))
    header = f"{'band':<8} {'1yr':>8} {'2yr':>8} {'50shows':>8} {'100shows':>8}  {'best':>8}"
    print(header)
    print("-" * len(header))

    for band in bands_seen:
        row = {"band": band}
        for r in results:
            if r["band"] == band and "dual" in r:
                row[r["variant"]] = r["dual"]
        vals = {v: row.get(v, float("nan")) for v in ["1yr", "2yr", "50", "100"]}
        best = max(vals, key=lambda k: vals.get(k, 0))
        print(
            f"{band:<8} {vals['1yr']:>8.4f} {vals['2yr']:>8.4f} "
            f"{vals['50']:>8.4f} {vals['100']:>8.4f}  {best:>8}"
        )

    print(f"\nFull results: {out_path}")


if __name__ == "__main__":
    main()
