#!/usr/bin/env python3
"""Quick script to check WSP CK+ prediction data integrity."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from jambandnerd.db.db_utils import get_table_as_dataframe


def main():
    """Check WSP CK+ data for potential issues."""
    print("Checking WSP CK+ prediction data...")
    
    try:
        # Load CK+ predictions
        df = get_table_as_dataframe('predictions_ckplus')
        
        if df.empty:
            print("No CK+ prediction data found")
            return
        
        # Filter for WSP
        wsp_data = df[df['band'].str.lower() == 'wsp'].copy()
        
        if wsp_data.empty:
            print("No WSP CK+ data found")
            return
        
        print(f"Total WSP CK+ predictions: {len(wsp_data)}")
        print(f"Prediction date: {wsp_data['prediction_date'].iloc[0]}")
        
        # Sort by CK+ score and show top 10
        wsp_sorted = wsp_data.sort_values('ckplus_score', ascending=False).head(10)
        
        print("\nTop 10 WSP CK+ Predictions:")
        print("=" * 80)
        for _, row in wsp_sorted.iterrows():
            print(f"{row['song_name']:<25} | Gap: {row['current_gap']:<3} | Score: {row['ckplus_score']:<6.2f} | LTP: {row['last_played_date']}")
        
        # Check for data anomalies
        print(f"\nCurrent gap statistics:")
        print(f"Min: {wsp_data['current_gap'].min()}")
        print(f"Max: {wsp_data['current_gap'].max()}")
        print(f"Mean: {wsp_data['current_gap'].mean():.2f}")
        
        # Check for suspicious values
        high_gaps = wsp_data[wsp_data['current_gap'] > 1000]
        if not high_gaps.empty:
            print(f"\nSongs with suspiciously high gaps (>1000):")
            for _, row in high_gaps.iterrows():
                print(f"  {row['song_name']}: {row['current_gap']} shows")
        
        # Check for negative gaps
        negative_gaps = wsp_data[wsp_data['current_gap'] < 0]
        if not negative_gaps.empty:
            print(f"\nSongs with negative gaps:")
            for _, row in negative_gaps.iterrows():
                print(f"  {row['song_name']}: {row['current_gap']} shows")
        
    except Exception as e:
        print(f"Error checking WSP data: {e}")


if __name__ == "__main__":
    main()
