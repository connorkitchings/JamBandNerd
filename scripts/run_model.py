"""Unified script for running models, predictions, and backtesting."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Run JamBandNerd models.")
    parser.add_argument("model", choices=["notebook", "ckplus"], help="The model to run.")
    parser.add_argument("action", choices=["predict", "backtest"], help="The action to perform.")
    parser.add_argument("--date", help="Reference show date YYYY-MM-DD for predictions.")
    parser.add_argument("--start", help="Start date YYYY-MM-DD for backtesting.")
    parser.add_argument("--end", help="End date YYYY-MM-DD for backtesting.")
    parser.add_argument("--shows", type=int, default=50, help="Number of recent shows for accuracy summary.")
    parser.add_argument("--skip-validation", action="store_true", help="Bypass schema validation.")

    args = parser.parse_args()

    if args.action == "predict":
        print(f"Running {args.model} model predictions for date: {args.date}")
        # Add prediction logic here
    elif args.action == "backtest":
        print(f"Running {args.model} model backtest from {args.start} to {args.end}")
        # Add backtesting logic here

if __name__ == "__main__":
    main()
