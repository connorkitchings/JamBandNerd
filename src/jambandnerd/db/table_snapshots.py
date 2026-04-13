"""Helpers for exporting and loading local table snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temp_path.replace(path)


def _snapshot_root(snapshot_root: str | Path) -> Path:
    return snapshot_root if isinstance(snapshot_root, Path) else Path(snapshot_root)


def table_snapshot_path(table_name: str, snapshot_root: str | Path) -> Path:
    """Return the canonical JSON path for a table snapshot."""

    root = _snapshot_root(snapshot_root)
    return root / f"{table_name}.json"


def manifest_path(snapshot_root: str | Path) -> Path:
    """Return the manifest path for a snapshot directory."""

    root = _snapshot_root(snapshot_root)
    return root / MANIFEST_NAME


def load_snapshot_manifest(snapshot_root: str | Path) -> dict[str, Any] | None:
    """Load the snapshot manifest if it exists."""

    path = manifest_path(snapshot_root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise RuntimeError(f"Snapshot manifest has invalid shape: {path}")
    return payload


def write_snapshot_manifest(snapshot_root: str | Path, payload: dict[str, Any]) -> Path:
    """Write a snapshot manifest atomically."""

    path = manifest_path(snapshot_root)
    _write_json_atomic(path, payload)
    return path


def load_table_snapshot(
    table_name: str,
    snapshot_root: str | Path,
) -> list[dict[str, Any]]:
    """Load one table snapshot from disk."""

    path = table_snapshot_path(table_name, snapshot_root)
    if not path.exists():
        raise FileNotFoundError(f"Snapshot for {table_name} not found: {path}")

    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise RuntimeError(f"Snapshot payload has invalid shape: {path}")

    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise RuntimeError(f"Snapshot rows missing or invalid for {table_name}: {path}")
    return [row for row in rows if isinstance(row, dict)]


def write_table_snapshot(
    table_name: str,
    rows: list[dict[str, Any]],
    snapshot_root: str | Path,
) -> Path:
    """Write a single table snapshot atomically."""

    path = table_snapshot_path(table_name, snapshot_root)
    payload = {
        "table_name": table_name,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "rows": rows,
    }
    _write_json_atomic(path, payload)
    return path
