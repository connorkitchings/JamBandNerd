# Goose promotion-readiness review

Offline review for `goose_fast_rank_v1_candidate_relaxed_special_nbtop10`. No registry or production wiring changes are made by this report.

## Recommendation: `promote_after_separate_production_wiring_task`

- Candidate beats the registered Goose model and Notebook floor on dual, p@25, r@50, and F1@25 while matching Notebook p@10.
- Segment gains are strongest on Not Part of a Tour shows.
- Normal-tour segment has no p@10, p@25, or F1@25 degradation versus registered Goose.
- Candidate p@10 matches the Notebook floor on every aligned show and in aggregate. The JSONL artifacts do not store prediction song lists, so exact top-10 song-order confirmation remains covered by tests/models/test_goose_model.py::test_candidate_rank_guard_keeps_notebook_top_10. The product tradeoff is that ranks 1-10 remain rule-guarded by the Notebook floor while ranks 11-50 carry the relaxed candidate repair.

## Overall scorecard

| model | role | n | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `goose_fast_rank_v1` | Registered Goose | 100 | 0.4087 | 0.2740 | 0.2164 | 0.5433 | 0.2801 |
| `goose_notebook_floor_v1` | Notebook floor | 100 | 0.4076 | 0.2840 | 0.2156 | 0.5311 | 0.2790 |
| `goose_fast_rank_v1_candidate_relaxed_special_nbtop10` | promotion candidate | 100 | 0.4428 | 0.2840 | 0.2276 | 0.6016 | 0.2955 |
| `goose_fast_rank_v1_candidate_relaxed_global_nbtop10` | Global relaxed + Notebook top 10 control | 100 | 0.4803 | 0.2840 | 0.2400 | 0.6767 | 0.3121 |

## Candidate deltas

| comparison | segment | n | delta p@10 | delta p@25 | delta r@50 | delta F1@25 | delta dual proxy |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `candidate_vs_registered` | all | 100 | 0.0100 | 0.0112 | 0.0583 | 0.0153 | 0.0341 |
| `candidate_vs_registered` | special | 19 | 0.0316 | 0.0589 | 0.3066 | 0.0807 | 0.1691 |
| `candidate_vs_registered` | normal | 81 | 0.0049 | 0.0000 | 0.0000 | 0.0000 | 0.0025 |
| `candidate_vs_notebook` | all | 100 | 0.0000 | 0.0120 | 0.0705 | 0.0165 | 0.0352 |
| `candidate_vs_notebook` | special | 19 | 0.0000 | 0.0589 | 0.2986 | 0.0804 | 0.1493 |
| `candidate_vs_notebook` | normal | 81 | 0.0000 | 0.0010 | 0.0170 | 0.0015 | 0.0085 |
| `candidate_vs_global_control` | all | 100 | 0.0000 | -0.0124 | -0.0751 | -0.0166 | -0.0375 |
| `candidate_vs_global_control` | special | 19 | 0.0000 | -0.0084 | 0.0185 | -0.0106 | 0.0092 |
| `candidate_vs_global_control` | normal | 81 | 0.0000 | -0.0133 | -0.0970 | -0.0180 | -0.0485 |

## Segments

### registered

| segment | n | p@10 | p@25 | r@50 | F1@25 | dual proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 100 | 0.2740 | 0.2164 | 0.5433 | 0.2801 | 0.4087 |
| special | 19 | 0.2211 | 0.1663 | 0.3577 | 0.2094 | 0.2894 |
| normal | 81 | 0.2864 | 0.2281 | 0.5869 | 0.2967 | 0.4366 |

### notebook

| segment | n | p@10 | p@25 | r@50 | F1@25 | dual proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 100 | 0.2840 | 0.2156 | 0.5311 | 0.2790 | 0.4076 |
| special | 19 | 0.2526 | 0.1663 | 0.3657 | 0.2097 | 0.3092 |
| normal | 81 | 0.2914 | 0.2272 | 0.5699 | 0.2952 | 0.4306 |

### candidate

| segment | n | p@10 | p@25 | r@50 | F1@25 | dual proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 100 | 0.2840 | 0.2276 | 0.6016 | 0.2955 | 0.4428 |
| special | 19 | 0.2526 | 0.2253 | 0.6643 | 0.2901 | 0.4585 |
| normal | 81 | 0.2914 | 0.2281 | 0.5869 | 0.2967 | 0.4391 |

### global_control

| segment | n | p@10 | p@25 | r@50 | F1@25 | dual proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 100 | 0.2840 | 0.2400 | 0.6767 | 0.3121 | 0.4803 |
| special | 19 | 0.2526 | 0.2337 | 0.6458 | 0.3007 | 0.4492 |
| normal | 81 | 0.2914 | 0.2415 | 0.6839 | 0.3148 | 0.4876 |

## Top-10 guard

- Compared shows: 100
- Shows with Notebook-matching p@10 metric: 100
- Aggregate p@10 matches Notebook: True
- Mismatched show ids: none
- Interpretation: Candidate p@10 matches the Notebook floor on every aligned show and in aggregate. The JSONL artifacts do not store prediction song lists, so exact top-10 song-order confirmation remains covered by tests/models/test_goose_model.py::test_candidate_rank_guard_keeps_notebook_top_10. The product tradeoff is that ranks 1-10 remain rule-guarded by the Notebook floor while ranks 11-50 carry the relaxed candidate repair.
