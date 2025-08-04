#!/usr/bin/env python3
"""
Monitor WSP Cache Performance

This script analyzes the WSP pipeline logs to monitor cache performance
and verify that the caching mechanism is working correctly.

Usage:
    python monitor_wsp_cache.py [--log-file PATH] [--days DAYS]

Options:
    --log-file PATH    Path to the WSP log file (default: logs/WSP/wsp_pipeline.log)
    --days DAYS        Number of days of logs to analyze (default: 7)
"""

import argparse
import datetime
import os
import re

import matplotlib.pyplot as plt
import pandas as pd


def parse_log_file(log_file: str, days: int = 7) -> list[dict]:
    """
    Parse the WSP pipeline log file and extract relevant cache information.
    
    Args:
        log_file: Path to the log file
        days: Number of days to look back
    
    Returns:
        List of parsed log entries containing parsed log entries
    """
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return []
    
    # Calculate cutoff date
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Regex patterns
    date_pattern = r"\[(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})\]"
    cache_hit_pattern = r"Skipping (show|song) scraping \(using cached data\)"
    cache_miss_pattern = r"Scraping WSP (show|song) .* \(cache expired or missing\)"
    execution_time_pattern = r"WSP pipeline completed in (\d+\.\d+) seconds"
    setlist_count_pattern = r"Scraped (\d+) setlists"
    
    entries = []
    current_entry = None
    
    with open(log_file) as f:
        for line in f:
            # Check for new log entry
            date_match = re.search(date_pattern, line)
            if date_match:
                log_date = date_match.group(1)
                log_date_obj = datetime.datetime.strptime(log_date, "%m-%d-%Y %H:%M:%S")
                
                # Skip entries older than cutoff
                if log_date_obj < cutoff_date:
                    continue
                
                # If we find a start message, create a new entry
                if "Starting optimized WSP data ingestion pipeline" in line:
                    if current_entry:
                        entries.append(current_entry)
                    current_entry = {
                        "date": log_date,
                        "show_cache_hit": False,
                        "song_cache_hit": False,
                        "execution_time": None,
                        "setlist_count": 0,
                    }
            
            if not current_entry:
                continue
                
            # Check for cache hits
            cache_hit = re.search(cache_hit_pattern, line)
            if cache_hit:
                cache_type = cache_hit.group(1)
                if cache_type == "show":
                    current_entry["show_cache_hit"] = True
                elif cache_type == "song":
                    current_entry["song_cache_hit"] = True
            
            # Check for cache misses
            cache_miss = re.search(cache_miss_pattern, line)
            if cache_miss:
                cache_type = cache_miss.group(1)
                if cache_type == "show":
                    current_entry["show_cache_hit"] = False
                elif cache_type == "song":
                    current_entry["song_cache_hit"] = False
            
            # Check for execution time
            time_match = re.search(execution_time_pattern, line)
            if time_match:
                current_entry["execution_time"] = float(time_match.group(1))
            
            # Check for setlist scraping
            setlist_match = re.search(setlist_count_pattern, line)
            if setlist_match:
                current_entry["setlist_count"] = int(setlist_match.group(1))
    
    # Add the last entry if it exists
    if current_entry:
        entries.append(current_entry)
    
    return entries


def analyze_cache_performance(entries: list[dict]) -> dict:
    """
    Analyze cache performance metrics from log entries.
    
    Args:
        entries: List of parsed log entries
        
    Returns:
        Dictionary of performance metrics
    """
    if not entries:
        return {
            "total_runs": 0,
            "show_cache_hit_rate": 0,
            "song_cache_hit_rate": 0,
            "avg_execution_time": 0,
            "avg_execution_time_cache_hit": 0,
            "avg_execution_time_cache_miss": 0,
            "avg_setlist_count": 0,
        }
    
    total_runs = len(entries)
    show_cache_hits = sum(1 for entry in entries if entry["show_cache_hit"])
    song_cache_hits = sum(1 for entry in entries if entry["song_cache_hit"])
    
    # Calculate execution times
    execution_times = [entry["execution_time"] for entry in entries if entry["execution_time"] is not None]
    execution_times_cache_hit = [
        entry["execution_time"] 
        for entry in entries 
        if entry["execution_time"] is not None and entry["show_cache_hit"] and entry["song_cache_hit"]
    ]
    execution_times_cache_miss = [
        entry["execution_time"] 
        for entry in entries 
        if entry["execution_time"] is not None and (not entry["show_cache_hit"] or not entry["song_cache_hit"])
    ]
    
    # Calculate setlist counts
    setlist_counts = [entry["setlist_count"] for entry in entries]
    
    return {
        "total_runs": total_runs,
        "show_cache_hit_rate": show_cache_hits / total_runs if total_runs > 0 else 0,
        "song_cache_hit_rate": song_cache_hits / total_runs if total_runs > 0 else 0,
        "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
        "avg_execution_time_cache_hit": sum(execution_times_cache_hit) / len(execution_times_cache_hit) if execution_times_cache_hit else 0,
        "avg_execution_time_cache_miss": sum(execution_times_cache_miss) / len(execution_times_cache_miss) if execution_times_cache_miss else 0,
        "avg_setlist_count": sum(setlist_counts) / len(setlist_counts) if setlist_counts else 0,
    }


def generate_report(entries: list[dict], metrics: dict) -> str:
    """
    Generate a performance report based on the metrics.
    
    Args:
        entries: List of parsed log entries
        metrics: Dictionary of performance metrics
        
    Returns:
        Report string
    """
    report = "# WSP Cache Performance Report\n\n"
    
    # Summary statistics
    report += "## Summary Statistics\n\n"
    report += f"- **Total Pipeline Runs**: {metrics['total_runs']}\n"
    report += f"- **Show Cache Hit Rate**: {metrics['show_cache_hit_rate']:.1%}\n"
    report += f"- **Song Cache Hit Rate**: {metrics['song_cache_hit_rate']:.1%}\n"
    report += f"- **Average Execution Time**: {metrics['avg_execution_time']:.2f} seconds\n"
    report += f"- **Average Execution Time (Cache Hit)**: {metrics['avg_execution_time_cache_hit']:.2f} seconds\n"
    report += f"- **Average Execution Time (Cache Miss)**: {metrics['avg_execution_time_cache_miss']:.2f} seconds\n"
    report += f"- **Average Setlist Count**: {metrics['avg_setlist_count']:.1f}\n\n"
    
    # Performance improvement
    if metrics['avg_execution_time_cache_hit'] > 0 and metrics['avg_execution_time_cache_miss'] > 0:
        improvement = (metrics['avg_execution_time_cache_miss'] - metrics['avg_execution_time_cache_hit']) / metrics['avg_execution_time_cache_miss']
        report += f"## Performance Improvement\n\n"
        report += f"Cache hits improve execution time by **{improvement:.1%}** compared to cache misses.\n\n"
    
    # Recent runs table
    report += "## Recent Pipeline Runs\n\n"
    report += "| Date | Show Cache | Song Cache | Execution Time (s) | Setlist Count |\n"
    report += "|------|------------|------------|-------------------|---------------|\n"
    
    for entry in sorted(entries, key=lambda x: x["date"], reverse=True)[:10]:
        show_cache = "✅" if entry["show_cache_hit"] else "❌"
        song_cache = "✅" if entry["song_cache_hit"] else "❌"
        exec_time = f"{entry['execution_time']:.2f}" if entry["execution_time"] is not None else "N/A"
        report += f"| {entry['date']} | {show_cache} | {song_cache} | {exec_time} | {entry['setlist_count']} |\n"
    
    # Recommendations
    report += "\n## Recommendations\n\n"
    
    if metrics['show_cache_hit_rate'] < 0.8 or metrics['song_cache_hit_rate'] < 0.8:
        report += "- **Cache Tuning**: Consider increasing the cache expiration period (currently 7 days) to improve hit rate.\n"
    
    if metrics['avg_execution_time'] > 60:
        report += "- **Performance Optimization**: Pipeline execution time is high. Consider additional optimizations.\n"
    
    if metrics['avg_setlist_count'] < 10:
        report += "- **Data Completeness**: Low average setlist count may indicate issues with data collection.\n"
    
    return report


def plot_performance(entries: list[dict], output_file: str = "wsp_cache_performance.png") -> None:
    """
    Generate a performance plot based on the log entries.
    
    Args:
        entries: List of parsed log entries
        output_file: Path to save the plot
    """
    if not entries:
        return
    
    # Convert to DataFrame for easier plotting
    df = pd.DataFrame(entries)
    df["date"] = pd.to_datetime(df["date"], format="%m-%d-%Y %H:%M:%S")
    df = df.sort_values("date")
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Plot execution time
    ax1.plot(df["date"], df["execution_time"], marker="o", linestyle="-", label="Execution Time")
    ax1.set_ylabel("Execution Time (seconds)")
    ax1.set_title("WSP Pipeline Performance")
    ax1.grid(True)
    ax1.legend()
    
    # Plot cache hits
    ax2.plot(df["date"], df["show_cache_hit"].astype(int), marker="s", linestyle="-", label="Show Cache Hit")
    ax2.plot(df["date"], df["song_cache_hit"].astype(int), marker="^", linestyle="-", label="Song Cache Hit")
    ax2.set_ylabel("Cache Hit (1=Yes, 0=No)")
    ax2.set_xlabel("Date")
    ax2.grid(True)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Performance plot saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Monitor WSP cache performance")
    parser.add_argument(
        "--log-file", 
        default="logs/WSP/wsp_pipeline.log",
        help="Path to the WSP log file"
    )
    parser.add_argument(
        "--days", 
        type=int,
        default=7,
        help="Number of days of logs to analyze"
    )
    parser.add_argument(
        "--output", 
        default="wsp_cache_report.md",
        help="Output file for the report"
    )
    parser.add_argument(
        "--plot", 
        action="store_true",
        help="Generate performance plot"
    )
    args = parser.parse_args()
    
    # Parse logs
    print(f"Analyzing WSP logs from the last {args.days} days...")
    entries = parse_log_file(args.log_file, args.days)
    
    if not entries:
        print("No log entries found for the specified period.")
        return
    
    print(f"Found {len(entries)} pipeline runs.")
    
    # Analyze performance
    metrics = analyze_cache_performance(entries)
    
    # Generate report
    report = generate_report(entries, metrics)
    
    # Save report
    with open(args.output, "w") as f:
        f.write(report)
    print(f"Report saved to {args.output}")
    
    # Generate plot if requested
    if args.plot:
        plot_performance(entries)


if __name__ == "__main__":
    main()
