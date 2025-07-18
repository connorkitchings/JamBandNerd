"""
Script to run all predict_today.py scripts for Goose, Phish, and WSP
(CK+ and Notebook models for each) in parallel.
A placeholder is included for UM.
"""

import concurrent.futures
import logging
import subprocess
import sys
from pathlib import Path

import yaml

# Setup logging
log_file = Path("logs/run_all_predict_todays.log")
log_file.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)


def load_config():
    """Loads the pipeline configuration from the YAML file."""
    config_path = Path("config/predict_pipelines.yaml")
    if not config_path.exists():
        logging.error("Configuration file not found: %s", config_path)
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Convert string paths to Path objects
    predict_scripts = config.get("predict_scripts", {})
    return {label: Path(path) for label, path in predict_scripts.items()}


PREDICT_SCRIPTS = load_config()


def run_script(label, script_path):
    """Runs a prediction script and captures its output."""
    logging.info("Starting %s (%s)...", label, script_path)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute timeout for each script
        )
        return label, True, result.stdout, ""
    except subprocess.CalledProcessError as e:
        return label, False, e.stdout, e.stderr
    except subprocess.TimeoutExpired as e:
        return label, False, "", f"Timeout expired after {e.timeout} seconds."
    except Exception as e:
        return label, False, "", f"An unexpected error occurred: {e}"


def main():
    """Runs all prediction scripts in parallel."""
    logging.info("=== Starting all prediction pipelines ===")

    futures = {}
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for label, script_path in PREDICT_SCRIPTS.items():
            if not script_path.exists():
                logging.warning("Script not found, skipping: %s", script_path)
                continue
            future = executor.submit(run_script, label, script_path)
            futures[future] = label

        for future in concurrent.futures.as_completed(futures):
            label, success, stdout, stderr = future.result()
            if success:
                logging.info("%s completed successfully.", label)
                if stdout:
                    logging.info("Output for %s:\n%s", label, stdout)
            else:
                logging.error("Error running %s:", label)
                if stdout:
                    logging.error("STDOUT:\n%s", stdout)
                if stderr:
                    logging.error("STDERR:\n%s", stderr)

    logging.info("\n=== UM predict_today scripts placeholder ===")
    logging.info("UM prediction scripts not yet implemented.")
    logging.info("=== All prediction pipelines finished. ===")


if __name__ == "__main__":
    main()
