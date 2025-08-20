"""Generate Goose next-song predictions using the CK+ gap-based predictor."""
from __future__ import annotations

from typing import Any, Dict, List
import argparse
import os
import sys

import pandas as pd

# Align sys.path with other scripts
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.models.ckplus.model import CKPlusPredictor  # noqa: E402
from src.jambandnerd.db.operations import get_table_schema  # noqa: E402
from src.jambandnerd.db.validation import coerce_df_types, validate_dataframe_against_table  # noqa: E402


def _fetch_table(table: str, select: str = "*") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table(table).select(select).execute()
    return res.data or []


def _resolve_reference_show_date() -> str:
    from datetime import date
    client = get_supabase_client()
    shows_rows = client.table("goose_shows_raw").select("show_date,show_id").execute().data
    df = pd.DataFrame(shows_rows)
    df["_dt"] = pd.to_datetime(df["show_date"]).dt.date
    today = date.today()
    upcoming = df[df["_dt"] >= today].sort_values(["_dt", "show_id"])  # earliest show date >= today
    if not upcoming.empty:
        d = upcoming.iloc[0]["_dt"]
    else:
        d = df["_dt"].max()
    return d.isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Goose CK+ predictions")
    parser.add_argument("--date", dest="date", help="Reference show date YYYY-MM-DD", required=False)
    parser.add_argument("--skip-validation", action="store_true", help="Bypass schema validation for inputs and outputs")
    parser.add_argument("--top-k", dest="top_k", type=int, default=50)
    args = parser.parse_args()

    print("Loading Goose raw tables from Supabase...")
    shows_rows = _fetch_table("goose_shows_raw")
    setlists_rows = _fetch_table("goose_setlists_raw")
    shows_df = pd.DataFrame(shows_rows)
    setlists_df = pd.DataFrame(setlists_rows)
    print(f"Loaded shows={len(shows_df)}, setlists={len(setlists_df)}")

    if not args.skip_validation:
        for table_name, df_ref in (("goose_shows_raw", shows_df), ("goose_setlists_raw", setlists_df)):
            schema = get_table_schema(table_name)
            if schema and not df_ref.empty:
                tmp = coerce_df_types(df_ref, schema)
                report = validate_dataframe_against_table(tmp, table_name, schema)
                if report.is_valid:
                    if table_name == "goose_shows_raw":
                        shows_df = tmp
                    else:
                        setlists_df = tmp
                else:
                    print(f"Warning: {table_name} input validation failed: {report}")

    reference_date_str = args.date or _resolve_reference_show_date()
    predictor = CKPlusPredictor()
    predictions = predictor.predict(
        shows_df=shows_df,
        setlists_df=setlists_df,
        top_k=args.top_k,
        reference_show_date=pd.to_datetime(reference_date_str).date(),
    )

    print("Top predictions (CK+):")
    for rank, p in enumerate(predictions, start=1):
        print(
            f"{rank:2d}. {p.song_name} (plays={p.times_played}, gap={p.current_gap}, avg_gap={p.avg_gap:.1f}, "
            f"ratio={p.gap_ratio:.2f}, z={p.gap_z_score:.2f}, score={p.ckplus_score:.3f}, LTP={p.LTP})"
        )

    # Persist to Supabase CK+ predictions table (unified by model)
    payload = [
        {
            "rank": i + 1,
            "song_name": p.song_name,
            "times_played": p.times_played,
            "current_gap": p.current_gap,
            "avg_gap": p.avg_gap,
            "gap_ratio": p.gap_ratio,
            "gap_z_score": p.gap_z_score,
            "ckplus_score": p.ckplus_score,
            "LTP": p.LTP,
        }
        for i, p in enumerate(predictions)
    ]

    client = get_supabase_client()
    record = {
        "band": "goose",
        "reference_date": pd.to_datetime(reference_date_str).date().isoformat(),
        "predictions": payload,
        "top_k": len(payload),
        "model_version": "ckplus_v1",
        "predicted_at": pd.Timestamp.utcnow().isoformat(),
    }
    if not args.skip_validation:
        out_schema = get_table_schema("predictions_ckplus")
        if out_schema:
            tmp_df = pd.DataFrame([record])
            tmp_df = coerce_df_types(tmp_df, out_schema)
            out_report = validate_dataframe_against_table(tmp_df, "predictions_ckplus", out_schema)
            if not out_report.is_valid:
                print(f"Warning: predictions_ckplus output validation failed: {out_report}")

    client.table("predictions_ckplus").upsert(record, on_conflict="band,reference_date,model_version").execute()
    print("Saved predictions to predictions_ckplus.")


if __name__ == "__main__":
    main()



