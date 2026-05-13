# Model headroom report

Production baselines are frozen to the single-model-per-band registry. This report ranks follow-up work without promoting experiments.

## Baseline scorecard

| band | model_version | n | dual | p@10 | p@25 | r@50 | F1@25 | delta dual | delta F1@25 | miss proxy | recommendation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| goose | `goose_fast_rank_v1` | 100 | 0.4087 | 0.2740 | 0.2164 | 0.5433 | 0.2801 | n/a | n/a | 0.4567 | `architecture_spike_if_diagnostics_support` |
| phish | `phish_fast_gbm_v2_feat_notebook_rank_venue_run` | 99 | 0.4186 | 0.2929 | 0.2453 | 0.5442 | 0.2831 | 0.0138 | 0.0084 | 0.4558 | `cleanup_ablation` |
| wsp | `wsp_fast_gbm_v2` | 100 | 0.4484 | 0.3290 | 0.2980 | 0.5678 | 0.3248 | 0.0141 | 0.0167 | 0.4322 | `hold_upstream_recovery` |
| billy | `billy_fast_gbm_v10_hp_tuned` | 100 | 0.3879 | 0.3330 | 0.2848 | 0.4428 | 0.2848 | 0.0110 | 0.0063 | 0.5572 | `hold_upstream_recovery` |
| um | `um_fast_gbm_v2` | 100 | 0.3431 | 0.1990 | 0.1704 | 0.4872 | 0.2137 | 0.0201 | 0.0086 | 0.5128 | `hold_monitor_prod_drift` |

## Worst-show segments

### goose

- Current ranker is only narrowly ahead of the Notebook floor; avoid more feature/HP sweeps unless diagnostics show a miss pattern.

| show_id | target_show_date | actual songs | F1@25 | r@50 |
| --- | --- | ---: | ---: | ---: |
| `1745515491` | 2025-07-25 | 4 | 0.0000 | 0.0000 |
| `1754580823` | 2025-08-15 | 8 | 0.0000 | 0.0000 |
| `1737731867` | 2025-06-22 | 12 | 0.0541 | 0.4167 |

### phish

- Only band with a documented cleanup path after show-type failed promotion.

| show_id | target_show_date | actual songs | F1@25 | r@50 |
| --- | --- | ---: | ---: | ---: |
| `1723666648` | 2024-08-14 | 8 | 0.0000 | 0.0000 |
| `1738096515` | 2025-01-28 | 3 | 0.0000 | 0.0000 |
| `1764702334` | 2026-04-17 | 19 | 0.0000 | 0.2632 |

### wsp

- Current WSP V2 is at local optimum and live validation is blocked by recent Everyday Companion source gaps.

| show_id | target_show_date | actual songs | F1@25 | r@50 |
| --- | --- | ---: | ---: | ---: |
| `13959` | 2024-06-20 | 6 | 0.0645 | 0.5000 |
| `13964` | 2025-02-15 | 19 | 0.0909 | 0.2632 |
| `13978` | 2025-06-28 | 21 | 0.1304 | 0.3810 |

### billy

- Current Billy V10 is at local optimum and live validation is blocked by bmfsdb.com reachability.

| show_id | target_show_date | actual songs | F1@25 | r@50 |
| --- | --- | ---: | ---: | ---: |
| `61` | 2025-03-02 | 34 | 0.0000 | 0.0000 |
| `10` | 2025-09-17 | 28 | 0.0000 | 0.0357 |
| `17` | 2025-09-05 | 31 | 0.0000 | 0.0645 |

### um

- Current UM V2 cleared the Phase B gain; hold unless production schema-sync fixes reveal drift.

| show_id | target_show_date | actual songs | F1@25 | r@50 |
| --- | --- | ---: | ---: | ---: |
| `1773756239` | 2026-04-30 | 11 | 0.0000 | 0.0909 |
| `1749864080` | 2025-06-13 | 8 | 0.0000 | 0.2500 |
| `1745437069` | 2025-04-19 | 6 | 0.0000 | 0.3333 |
