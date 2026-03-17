import json
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.operations import get_table_schema


def main():
    table_names = [
        "wsp_songs_raw",
        "wsp_shows_raw",
        "wsp_venues_raw",
        "wsp_setlists_raw",
        "predictions_notebook",
        "predictions_ckplus",
    ]
    schemas = {}
    for table in table_names:
        print(f"Fetching schema for {table}...")
        schemas[table] = get_table_schema(table)

    print("\n--- SCHEMAS ---")
    print(json.dumps(schemas, indent=2))


if __name__ == "__main__":
    main()
