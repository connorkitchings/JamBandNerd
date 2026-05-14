# Billy Strings Phase B — Module Scaffold

## Goal

Build a `models/billy/` module that adapts the Goose Phase B framework for Billy
Strings and promotes it as the production default (replacing BaselinePredictor).

## What Was Built

### New files

- `src/jambandnerd/models/billy/features.py` — All 10 Goose extra features
  (month_play_rate, run/tour-aware, recency windows, same-venue-run) plus `is_cover`
  (11th feature). `compute_billy_song_features()` accepts optional `songs_lookup` dict.
  `augment_training_frame()` adapted from goose with `songs_lookup` pass-through.

- `src/jambandnerd/models/billy/model.py` — `BillyPredictor` (logistic, DealPredictor
  subclass) and `BillyGbmPredictor` (GBM, BandGbmPredictor subclass). Both accept
  `songs_df=None` kwarg — if provided uses it directly; if None, loads from Supabase
  at init via `_fetch_songs_from_supabase()`. `_build_is_cover_lookup()` maps
  `original_artist → is_cover` (1.0 for covers, 0.0 for originals/None artists).

- `src/jambandnerd/models/billy/__init__.py` — Exports BillyPredictor, BillyGbmPredictor,
  BILLY_FEATURE_COLUMNS.

- `tests/models/test_billy_model.py` — 8 tests: defaults, band rejection (x2), train+
  predict smoke (x2), is_cover lookup correctness, lookup empty cases, registry check.

### Modified files

- `src/jambandnerd/models/metadata.py` — Updated billy model_version to `billy_phase_b_v1`
- `src/jambandnerd/models/registry.py` — Added `BillyPredictor` to `_BAND_PREDICTOR_CLASSES`

## Key Design Decisions

### `is_cover` feature
Billy's setlist DB (`billy_songs_raw`) has `original_artist`. If non-null (and not a
Billy alias), the song is a cover — fundamentally different rotation dynamics from
originals. Songs are loaded from Supabase once at predictor init; tests pass a
synthetic `songs_df` to avoid DB calls.

### Hyperparameter choices vs. Goose
- `retired_gap_threshold = 120` (Goose: 90; config: 150) — Billy's larger catalog
  warrants a more conservative retirement cutoff
- `training_window_shows = 75` (Goose: 60) — Billy tours heavily (~200+ shows/year);
  wider window captures more seasonal/rotational patterns
- `min_plays_threshold = 3` (same as Goose, lower than baseline's 5)
- `positive_weight_cap = 2.0` (same as Goose)

### Feature set
`BillyPredictor` starts immediately with `BILLY_V2_FEATURE_COLUMNS` (base + extras +
is_cover) since we're building on Goose's validated learnings. No v1 no-extras phase.

## Dataset
- 1,220 shows, 19,533 setlist records (Billy has ~50% more history than Goose)
- Snapshot: `.snapshots/billy_phase_b/` (created from Supabase 2026-04-30)

## Validation
- `uv run pytest tests/models/ -q`: **121 passed** (8 new Billy tests, no regressions)

## Status

Backtests running in background (started 2026-04-30 ~8:05 PM):
```bash
for pred in \
  jambandnerd.models.billy.model.BillyPredictor \
  jambandnerd.models.billy.model.BillyGbmPredictor; do
  uv run python scripts/run_phase_b_backtest.py \
      --band billy --predictor $pred --shows 100 \
      --snapshot-root .snapshots/billy_phase_b --out-dir backtests/
done
```

## Next Steps

1. Read backtest summary JSONs when they complete (~4 hours total)
2. Compare `dual_score` / `dual_f1_score` — decide whether logistic or GBM wins
3. If GBM wins: update `_BAND_PREDICTOR_CLASSES["billy"]` to `BillyGbmPredictor`
4. If logistic wins: keep `BillyPredictor` as default (already wired)
5. Write final session log with the comparison and decision
