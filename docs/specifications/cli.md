# CLI and Scripting Specification

This document defines the command-line interface and scripting design for JamBandNerd. The primary method for interacting with the project's data pipelines is through a series of Python scripts, which are designed to be run with `uv run`.

## Primary Pipeline Script

The main entry point for running the end-to-end pipeline is `scripts/run_optimized_pipeline.py`. This script is the recommended way to run the full data collection, transformation, prediction, and accuracy calculation process.

### Usage

```bash
# Run the complete pipeline for all supported bands
uv run python scripts/run_optimized_pipeline.py --band all

# Run the pipeline for a single band (e.g., Goose)
uv run python scripts/run_optimized_pipeline.py --band goose

# Skip accuracy calculations for a faster run
uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
```

## Individual Scripts

While the optimized pipeline is recommended, individual scripts can be run for more granular control or for debugging purposes. These scripts are located in the `scripts/` directory and are designed to be run with `uv run python <script_name>.py`.

### Future Considerations: `jbn` CLI

A `jbn` command-line tool, built with Typer, was originally planned for the project. This tool would provide a more user-friendly interface for running the various pipeline components. While the core logic is implemented in the Python scripts, the `jbn` CLI has been deferred to a future development phase.

