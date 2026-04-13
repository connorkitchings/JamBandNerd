"""Local cache helpers for model-development historical test runs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_MODEL_TEST_CACHE_ROOT = Path("docs/reports/model_baselines/cache")


def _stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip())
    return normalized.strip("-") or "artifact"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temp_path.replace(path)


def build_experiment_cache_identity(
    *,
    candidate_model: str,
    baseline_models: list[str],
    bands: list[str],
    windows: list[dict[str, Any]],
    exclusion_window: int,
    feature_set_label: str,
    fresh_training: bool,
    candidate_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_model": candidate_model,
        "baseline_models": list(baseline_models),
        "requested_bands": list(bands),
        "windows": [
            {"label": window["label"], "shows": window["shows"]} for window in windows
        ],
        "exclusion_window": exclusion_window,
        "feature_set_label": feature_set_label,
        "fresh_training": fresh_training,
        "candidate_overrides": candidate_overrides or None,
    }


def build_experiment_cache_key(identity: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json_dumps(identity).encode("utf-8")).hexdigest()
    return digest[:16]


def build_default_cache_dir(
    *,
    identity: dict[str, Any],
    cache_root: Path | None = None,
) -> Path:
    root = cache_root or DEFAULT_MODEL_TEST_CACHE_ROOT
    experiment_key = build_experiment_cache_key(identity)
    label = _safe_slug(
        f"{identity['candidate_model']}__{identity['feature_set_label']}__{experiment_key}"
    )
    return root / label


@dataclass
class LocalModelTestCache:
    """Disk-backed cache for one model-development experiment context."""

    cache_dir: Path
    experiment_identity: dict[str, Any]
    hits: int = 0
    misses: int = 0
    writes: int = 0
    experiment_key: str = field(init=False)

    def __post_init__(self) -> None:
        self.experiment_key = build_experiment_cache_key(self.experiment_identity)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_manifest()

    @property
    def manifest_path(self) -> Path:
        return self.cache_dir / "manifest.json"

    def _load_manifest(self) -> dict[str, Any] | None:
        if not self.manifest_path.exists():
            return None
        return json.loads(self.manifest_path.read_text())

    def _ensure_manifest(self) -> None:
        existing = self._load_manifest()
        if existing is not None:
            if existing.get("experiment_key") != self.experiment_key:
                raise RuntimeError(
                    f"Cache manifest mismatch at {self.manifest_path}: experiment key changed."
                )
            return

        _write_json_atomic(
            self.manifest_path,
            {
                "experiment_key": self.experiment_key,
                "experiment_identity": self.experiment_identity,
                "stats": {
                    "record_count": 0,
                },
            },
        )

    def _update_manifest_record_count(self, *, record_delta: int) -> None:
        manifest = self._load_manifest()
        if manifest is None:
            self._ensure_manifest()
            manifest = self._load_manifest() or {}
        stats = manifest.setdefault("stats", {})
        stats["record_count"] = int(stats.get("record_count", 0)) + record_delta
        _write_json_atomic(self.manifest_path, manifest)

    def _record_path(
        self,
        *,
        band: str,
        model_slug: str,
        reference_date: str,
        target_show_id: str,
    ) -> Path:
        suffix = hashlib.sha1(
            f"{reference_date}::{target_show_id}".encode("utf-8")
        ).hexdigest()[:12]
        return (
            self.cache_dir
            / "runs"
            / _safe_slug(band)
            / _safe_slug(model_slug)
            / f"{reference_date}__{suffix}.json"
        )

    def load_scored_run(
        self,
        *,
        band: str,
        model_slug: str,
        reference_date: str,
        target_show_id: str,
    ) -> dict[str, Any] | None:
        record_path = self._record_path(
            band=band,
            model_slug=model_slug,
            reference_date=reference_date,
            target_show_id=target_show_id,
        )
        if not record_path.exists():
            self.misses += 1
            return None

        self.hits += 1
        return json.loads(record_path.read_text())

    def write_scored_run(self, record: dict[str, Any]) -> None:
        record_path = self._record_path(
            band=str(record["band"]),
            model_slug=str(record["model_slug"]),
            reference_date=str(record["reference_date"]),
            target_show_id=str(record["show_id"]),
        )
        existed = record_path.exists()
        _write_json_atomic(record_path, record)
        self.writes += 1
        if not existed:
            self._update_manifest_record_count(record_delta=1)

    def build_summary(self) -> dict[str, Any]:
        runs_dir = self.cache_dir / "runs"
        record_count = (
            sum(1 for _ in runs_dir.rglob("*.json")) if runs_dir.exists() else 0
        )
        return {
            "cache_dir": str(self.cache_dir),
            "experiment_key": self.experiment_key,
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "record_count": record_count,
        }
