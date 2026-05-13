"""WSP per-show failure analysis.

Re-runs the backtest for bottom-N failure shows and captures per-song
predicted vs actual data with cover detection, rarity classification,
and candidate pruning diagnostics.

Usage:
  uv run python scripts/wsp_failure_analysis.py --bottom 12
  uv run python scripts/wsp_failure_analysis.py --show-dates 2023-10-28,2024-06-20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from jambandnerd.models.accuracy import compute_per_show_metrics
from jambandnerd.models.evaluation import (
    get_evaluation_reference_date,
    list_completed_shows,
)
from jambandnerd.models.wsp.fast_predictor import WSPFastPredictor
from jambandnerd.transformations.gaps import generate_model_data
from scripts.common import fetch_table, prepare_band_data

BAND = "wsp"
SNAPSHOT_ROOT = ".snapshots/wsp"
OUT_DIR = "backtests"
K_VALUES = [10, 25, 50]

WSP_COVERS: dict[str, str] = {
    "Crazy Train": "Ozzy Osbourne",
    "Iron Man": "Black Sabbath",
    "Mr. Crowley": "Ozzy Osbourne",
    "Snowblind": "Black Sabbath",
    "Sweet Leaf": "Black Sabbath",
    "Fairies Wear Boots": "Black Sabbath",
    "Heart of Gold": "Neil Young",
    "Piece of My Heart": "Big Brother & The Holding Co",
    "Running Down A Dream": "Tom Petty",
    "Over The Rainbow": "Judy Garland",
    "You Can't Always Get What You Want": "Rolling Stones",
    "Sympathy for the Devil": "Rolling Stones",
    "Waitin' For The Bus": "ZZ Top",
    "Jesus Just Left Chicago": "ZZ Top",
    "Low Spark Of High Heeled Boys": "Traffic",
    "Good Morning Little Schoolgirl": "Skip James/Cream",
    "I Walk On Guilded Splinters": "Dr. John",
    "Ride Me High": "JJ Cale",
    "Jessica": "Allman Brothers",
    "Me And The Devil Blues": "Robert Johnson",
    "No Sugar Tonight/New Mother Nature": "The Guess Who",
    "Nobody's Fault But Mine": "Led Zeppelin",
    "The Harder They Come": "Jimmy Cliff",
    "Iko Iko": "The Dixie Cups",
    "Fire on the Mountain": "Grateful Dead",
    "Not Fade Away": "Buddy Holly",
    "Sugaree": "Grateful Dead",
    "Bird Song": "Grateful Dead",
    "Morning Dew": "Bonnie Dobson/Grateful Dead",
    "I Know You Rider": "Traditional/Grateful Dead",
    "Knockin' On Heaven's Door": "Bob Dylan",
    "All Along The Watchtower": "Bob Dylan",
    "A Hard Rain's A-Gonna Fall": "Bob Dylan",
    "The Shape I'm In": "The Band",
    "Turn On Your Love Light": "Bobby Bland",
    "For What It's Worth": "Buffalo Springfield",
    "Superstition": "Stevie Wonder",
    "Thank You Falettinme Be Mice Elf Agin": "Sly & The Family Stone",
    "Wooden Ships": "CSN/Jefferson Airplane",
    "Riders On The Storm": "The Doors",
    "Time Is Free": "Col. Bruce Hampton",
    "Shouldn't Have Took More Than You Gave": "Dave Mason",
    "Spoonful": "Howlin' Wolf/Willie Dixon",
    "Junco Partner": "James Booker",
    "Chest Fever": "The Band",
    "The Ballad of John and Yoko": "The Beatles",
    "Stranger in a Strange Land": "Leon Russell",
    "Another Man Done Gone": "Traditional",
    "Heathen": "Sonny Landreth",
    "I'm So Glad": "Skip James/Cream",
    "Are You Ready For The Country?": "Neil Young",
    "Vampire Blues": "Neil Young",
    "Song For Sitara": "Freddy Jones Band",
    "Don't Tell The Band": "The Allman Brothers Band",
    "Honey Bee": "Tom Petty",
    "You Wreck Me": "Tom Petty",
    "Puppy Sleeps": "Acoustic Syndicate",
    "Keep Me in Your Heart": "Warren Zevon",
    "There Is A Time": "Del McCoury",
    "Life As A Tree": "Perpetual Groove",
    "Blue Carousel": "Perpetual Groove",
}


def _load_song_stats(setlist_rows: list[dict]) -> dict[str, dict[str, Any]]:
    total = len(set(r["show_id"] for r in setlist_rows))
    counts: Counter[str] = Counter()
    for r in setlist_rows:
        counts[r["song_name"]] += 1
    return {
        song: {"plays": c, "pct": c / max(1, total) * 100} for song, c in counts.items()
    }


def _build_show_songs(setlist_rows: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in setlist_rows:
        out.setdefault(str(r["show_id"]), []).append(r["song_name"])
    return {sid: sorted(set(songs)) for sid, songs in out.items()}


def _build_recent_songs(
    setlist_rows: list[dict], show_ids_ordered: list[int], window: int = 150
) -> dict[int, set[str]]:
    idx_map = {sid: i for i, sid in enumerate(show_ids_ordered)}
    sid_to_songs: dict[int, set[str]] = {}
    for r in setlist_rows:
        sid_to_songs.setdefault(r["show_id"], set()).add(r["song_name"])

    result: dict[int, set[str]] = {}
    for sid in show_ids_ordered:
        i = idx_map[sid]
        start = max(0, i - window)
        recent = set()
        for prev_sid in show_ids_ordered[start:i]:
            recent |= sid_to_songs.get(prev_sid, set())
        result[sid] = recent
    return result


def _build_top_career(song_stats: dict, n: int = 100) -> set[str]:
    ranked = sorted(song_stats.items(), key=lambda x: -x[1]["plays"])
    return {song for song, _ in ranked[:n]}


def _classify_rarity(pct: float) -> str:
    if pct > 10.0:
        return "core"
    if pct >= 1.0:
        return "occasional"
    return "rare"


def _identify_failure_shows(jsonl_path: str, bottom: int) -> list[dict]:
    records: list[dict] = []
    with open(jsonl_path) as fh:
        for line in fh:
            r = json.loads(line)
            r["_f1_25"] = r["metrics"]["k25"]["f1"]
            records.append(r)
    records.sort(key=lambda x: x["_f1_25"])
    return records[:bottom]


def analyze_show(
    *,
    show_row: pd.Series,
    sets_df: pd.DataFrame,
    predictor: WSPFastPredictor,
    shows_df: pd.DataFrame,
    recent_songs_map: dict[int, set[str]],
    top_career: set[str],
    song_stats: dict[str, dict[str, Any]],
    show_songs_map: dict[str, list[str]],
    shows_meta: dict[str, dict],
) -> dict[str, Any] | None:
    ref_date = show_row["show_date"]
    show_id = str(show_row["show_id"])
    if not isinstance(ref_date, date):
        ref_date = pd.Timestamp(ref_date).date()

    actual_songs = show_songs_map.get(show_id, [])
    if not actual_songs or len(actual_songs) <= 2:
        return None

    prediction_date = get_evaluation_reference_date(ref_date)

    try:
        model_data = generate_model_data(
            shows_df,
            sets_df,
            prediction_date,
            band=BAND,
            target_show_context=show_row,
        )
        predictor.train(model_data)
        predictions = predictor.predict(model_data, top_k=50)
        if isinstance(predictions, tuple):
            predictions = predictions[0]
        if not predictions:
            return None
    except Exception as exc:
        print(f"  [WARN] {show_id}: {exc}")
        return None

    pred_songs = [p.song_name for p in predictions]
    pred_lookup = {p.song_name: p for p in predictions}

    metrics_by_k = {
        k: compute_per_show_metrics(pred_songs, actual_songs, k) for k in K_VALUES
    }

    actual_set = set(actual_songs)
    top25_set = set(pred_songs[:25])
    hits_k25 = sorted(actual_set & top25_set)
    misses_k25 = sorted(actual_set - top25_set)
    false_pos_k25 = sorted(top25_set - actual_set)

    int_show_id = int(show_id)
    recent_set = recent_songs_map.get(int_show_id, set())

    miss_details: list[dict[str, Any]] = []
    for song in misses_k25:
        stats = song_stats.get(song, {"plays": 0, "pct": 0.0})
        in_recent = song in recent_set
        in_career = song in top_career
        is_candidate = in_recent or in_career
        pred = pred_lookup.get(song)
        miss_details.append(
            {
                "song_name": song,
                "is_cover": song in WSP_COVERS,
                "cover_artist": WSP_COVERS.get(song),
                "candidate_status": "in_candidates" if is_candidate else "pruned",
                "in_recent_150": in_recent,
                "in_top100_career": in_career,
                "predicted_rank": (predictions.index(pred) + 1) if pred else None,
                "predicted_probability": pred.probability if pred else None,
                "gap_shows": pred.gap_shows if pred else None,
                "career_plays": stats["plays"],
                "career_pct": round(stats["pct"], 2),
                "rarity": _classify_rarity(stats["pct"]),
            }
        )

    fp_details: list[dict[str, Any]] = []
    for song in false_pos_k25:
        pred = pred_lookup.get(song)
        stats = song_stats.get(song, {"plays": 0, "pct": 0.0})
        fp_details.append(
            {
                "song_name": song,
                "predicted_rank": (predictions.index(pred) + 1) if pred else None,
                "predicted_probability": pred.probability if pred else None,
                "career_plays": stats["plays"],
                "career_pct": round(stats["pct"], 2),
                "rarity": _classify_rarity(stats["pct"]),
            }
        )

    meta = shows_meta.get(show_id, {})
    cover_songs = [s for s in actual_songs if s in WSP_COVERS]
    pruned_misses = [m for m in miss_details if m["candidate_status"] == "pruned"]
    core_misses = [m for m in miss_details if m["rarity"] == "core"]

    return {
        "show_id": show_id,
        "show_date": ref_date.isoformat(),
        "venue_name": meta.get("venue_name"),
        "city": meta.get("city"),
        "state": meta.get("state"),
        "actual_song_count": len(actual_songs),
        "actual_songs": actual_songs,
        "predictions": [
            {
                "song_name": p.song_name,
                "rank": i + 1,
                "probability": round(p.probability, 4),
                "gap_shows": p.gap_shows,
            }
            for i, p in enumerate(predictions)
        ],
        "metrics": {f"k{k}": v for k, v in metrics_by_k.items()},
        "analysis": {
            "hits_k25": hits_k25,
            "misses_k25": miss_details,
            "false_positives_k25": fp_details,
            "cover_count": len(cover_songs),
            "cover_songs": cover_songs,
            "pruned_count": len(pruned_misses),
            "core_miss_count": len(core_misses),
            "short_set": len(actual_songs) < 15,
        },
    }


def print_summary(records: list[dict]) -> None:
    print("\n" + "=" * 70)
    print(f"WSP FAILURE ANALYSIS SUMMARY ({len(records)} shows)")
    print("=" * 70)

    total_misses = 0
    total_pruned = 0
    total_ranked_26_50 = 0
    total_ranked_below_50 = 0
    total_covers_in_actual = 0
    total_songs_actual = 0
    total_covers_missed = 0
    total_covers_pruned = 0
    total_core_misses = 0
    total_core_pruned = 0
    total_core_below_50 = 0
    total_core_26_50 = 0
    total_occasional_misses = 0
    total_rare_misses = 0
    total_short_set = 0
    short_set_f1s: list[float] = []
    normal_f1s: list[float] = []

    for r in records:
        a = r["analysis"]
        misses = a["misses_k25"]
        total_misses += len(misses)
        for m in misses:
            if m["candidate_status"] == "pruned":
                total_pruned += 1
            elif m["predicted_rank"] is not None and m["predicted_rank"] <= 50:
                total_ranked_26_50 += 1
            else:
                total_ranked_below_50 += 1

        covers = a["cover_songs"]
        total_covers_in_actual += len(covers)
        total_songs_actual += r["actual_song_count"]

        covers_missed = [m for m in misses if m["is_cover"]]
        total_covers_missed += len(covers_missed)
        covers_pruned = [m for m in covers_missed if m["candidate_status"] == "pruned"]
        total_covers_pruned += len(covers_pruned)

        for m in misses:
            if m["rarity"] == "core":
                total_core_misses += 1
                if m["candidate_status"] == "pruned":
                    total_core_pruned += 1
                elif m["predicted_rank"] is not None and m["predicted_rank"] <= 50:
                    total_core_26_50 += 1
                else:
                    total_core_below_50 += 1
            elif m["rarity"] == "occasional":
                total_occasional_misses += 1
            else:
                total_rare_misses += 1

        if a["short_set"]:
            total_short_set += 1
            short_set_f1s.append(r["metrics"]["k25"]["f1"])
        else:
            normal_f1s.append(r["metrics"]["k25"]["f1"])

    def pct(n: float) -> float:
        return n / max(1, total_misses) * 100

    print(f"\n{'─' * 70}")
    print("CANDIDATE STATUS OF MISSED SONGS")
    print(f"{'─' * 70}")
    print(f"  Total missed songs (not in top-25):           {total_misses}")
    print(
        f"  Pruned (not in candidate set):                {total_pruned} ({pct(total_pruned):.0f}%)"
    )
    print(
        f"  Candidate, ranked 26-50 (close):              {total_ranked_26_50} ({pct(total_ranked_26_50):.0f}%)"
    )
    print(
        f"  Candidate, ranked below 50 (far):             {total_ranked_below_50} ({pct(total_ranked_below_50):.0f}%)"
    )

    print(f"\n{'─' * 70}")
    print("COVER ANALYSIS")
    print(f"{'─' * 70}")
    print(
        f"  Covers in failure shows:                      {total_covers_in_actual}/{total_songs_actual} ({total_covers_in_actual / max(1, total_songs_actual) * 100:.1f}%)"
    )
    print(
        f"  Covers missed (not in top-25):                {total_covers_missed}/{total_covers_in_actual} ({total_covers_missed / max(1, total_covers_in_actual) * 100:.0f}%)"
    )
    print(
        f"  Covers pruned from candidates:                {total_covers_pruned}/{total_covers_missed} ({total_covers_pruned / max(1, total_covers_missed) * 100:.0f}%)"
    )

    print(f"\n{'─' * 70}")
    print("RARITY BREAKDOWN (missed songs)")
    print(f"{'─' * 70}")
    print(f"  Core misses (>10% career):      {total_core_misses}  ← ACTIONABLE")
    print(f"    Pruned from candidates:        {total_core_pruned}")
    print(f"    Ranked 26-50 (close):          {total_core_26_50}")
    print(f"    Ranked below 50 (far):         {total_core_below_50}")
    print(f"  Occasional misses (1-10%):       {total_occasional_misses}")
    print(f"  Rare misses (<1%):               {total_rare_misses}")

    print(f"\n{'─' * 70}")
    print("SHORT-SET IMPACT")
    print(f"{'─' * 70}")
    print(f"  Shows with <15 songs:           {total_short_set}/{len(records)}")
    if short_set_f1s:
        avg_short = sum(short_set_f1s) / len(short_set_f1s)
        print(f"  Avg F1@25 (short sets):         {avg_short:.3f}")
    if normal_f1s:
        avg_normal = sum(normal_f1s) / len(normal_f1s)
        print(f"  Avg F1@25 (normal sets):        {avg_normal:.3f}")

    print(f"\n{'─' * 70}")
    print("PER-SHOW BREAKDOWN")
    print(f"{'─' * 70}")
    print(
        f"  {'Date':<12} {'Venue':<30} {'Songs':>5} {'Covers':>6} {'F1@25':>6} {'Core Miss':>9}"
    )
    for r in records:
        a = r["analysis"]
        core = [m for m in a["misses_k25"] if m["rarity"] == "core"]
        venue = (r.get("venue_name") or "?")[:28]
        print(
            f"  {r['show_date']:<12} {venue:<30} {r['actual_song_count']:>5} "
            f"{a['cover_count']:>6} {r['metrics']['k25']['f1']:>6.3f} {len(core):>9}"
        )
        if core:
            for c in core:
                if c["candidate_status"] == "pruned":
                    rank_str = "NOT IN CANDIDATES"
                elif c["predicted_rank"] is not None:
                    rank_str = f"rank={c['predicted_rank']}"
                else:
                    rank_str = "rank>50 (below predictions)"
                gap_str = str(c["gap_shows"]) if c["gap_shows"] is not None else "n/a"
                print(
                    f"    -> {c['song_name']}: {rank_str}, gap={gap_str}, career={c['career_pct']:.1f}%"
                )

    print(f"\n{'─' * 70}")
    print("ACTIONABLE IMPROVEMENT SURFACE")
    print(f"{'─' * 70}")
    print(f"  Core rotation songs missed:     {total_core_misses} total")
    print(
        f"    Of those, ranked below top-50: {total_core_below_50} (model gives them near-zero probability)"
    )
    print(
        f"    Of those, ranked 26-50:        {total_core_26_50} (close — small score boost could help)"
    )
    print(
        f"    Of those, pruned:              {total_core_pruned} (wider candidate window needed)"
    )
    print("  Maximum F1@25 gain from core songs requires fixing rank>50 issue.")


def main() -> None:
    parser = argparse.ArgumentParser(description="WSP per-show failure analysis.")
    parser.add_argument(
        "--bottom",
        type=int,
        default=12,
        help="Number of worst shows to analyze (by F1@25).",
    )
    parser.add_argument(
        "--show-dates",
        type=str,
        default=None,
        help="Comma-separated show dates to analyze (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--snapshot-root",
        default=SNAPSHOT_ROOT,
        help="Local snapshot directory.",
    )
    parser.add_argument(
        "--out-dir",
        default=OUT_DIR,
        help="Output directory for JSONL results.",
    )
    args = parser.parse_args()

    shows_rows = fetch_table(f"{BAND}_shows_raw", snapshot_root=args.snapshot_root)
    setlist_rows = fetch_table(f"{BAND}_setlists_raw", snapshot_root=args.snapshot_root)
    shows_df = pd.DataFrame(shows_rows)
    sets_df = pd.DataFrame(setlist_rows)
    if shows_df.empty or sets_df.empty:
        raise RuntimeError(f"No data found for band '{BAND}'.")

    shows_df, sets_df = prepare_band_data(shows_df, sets_df, band=BAND)
    completed = list_completed_shows(shows_df, sets_df)

    jsonl_path = (
        Path(args.out_dir)
        / f"{BAND}_wsp_fast_gbm_v2_{len(completed.tail(100))}shows.jsonl"
    )

    if args.show_dates:
        target_dates = set(args.show_dates.split(","))
        target_shows = completed[completed["show_date"].astype(str).isin(target_dates)]
        if target_shows.empty:
            raise RuntimeError(f"No shows found for dates: {args.show_dates}")
    else:
        if not jsonl_path.exists():
            raise RuntimeError(
                f"Backtest JSONL not found: {jsonl_path}. Run Phase B backtest first."
            )
        failure_records = _identify_failure_shows(str(jsonl_path), args.bottom)
        failure_dates = {r["target_show_date"] for r in failure_records}
        target_shows = completed[completed["show_date"].astype(str).isin(failure_dates)]
        print(
            f"Identified {len(failure_records)} failure shows (F1@25 < {failure_records[-1]['_f1_25']:.3f})"
        )

    if target_shows.empty:
        raise RuntimeError("No target shows found.")

    song_stats = _load_song_stats(setlist_rows)
    show_songs_map = _build_show_songs(setlist_rows)
    top_career = _build_top_career(song_stats)
    shows_meta = {str(s["show_id"]): s for s in shows_rows}

    sorted_show_ids = sorted(set(r["show_id"] for r in setlist_rows))
    print("Building recent-song windows (this may take a moment)...")
    recent_songs_map = _build_recent_songs(setlist_rows, sorted_show_ids, window=150)

    predictor = WSPFastPredictor(band=BAND, persist_artifacts=False)

    print(f"\nAnalyzing {len(target_shows)} failure shows...")
    records: list[dict] = []
    total = len(target_shows)

    for idx, (_, show_row) in enumerate(target_shows.iterrows(), start=1):
        show_date = show_row["show_date"]
        if not isinstance(show_date, date):
            show_date = pd.Timestamp(show_date).date()
        print(f"  [{idx}/{total}] {show_date.isoformat()}", end="", flush=True)

        result = analyze_show(
            show_row=show_row,
            sets_df=sets_df,
            predictor=predictor,
            shows_df=shows_df,
            recent_songs_map=recent_songs_map,
            top_career=top_career,
            song_stats=song_stats,
            show_songs_map=show_songs_map,
            shows_meta=shows_meta,
        )
        if result:
            records.append(result)
            f1 = result["metrics"]["k25"]["f1"]
            n_miss = len(result["analysis"]["misses_k25"])
            n_core = result["analysis"]["core_miss_count"]
            print(f"  f1@25={f1:.3f}  misses={n_miss}  core_misses={n_core}")
        else:
            print("  [SKIP]")

    if not records:
        raise RuntimeError("No shows were successfully analyzed.")

    out_path = Path(args.out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    output_file = out_path / f"{BAND}_failure_analysis.jsonl"
    with output_file.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(f"\nResults written to: {output_file}")

    print_summary(records)


if __name__ == "__main__":
    main()
