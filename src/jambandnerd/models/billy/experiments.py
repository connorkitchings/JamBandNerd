"""Billy Strings experiment sweep configs.

Base incumbent: BillyFastPredictorV10 (16 V3 features, leaves=15,
min_leaf=10; dual=0.388).  HP sweeps start from V10 base via
``_BASE_PREDICTOR_PATHS``.  Feature/window sweeps use explicit
``predictor_path``.

Historical V3-based HP + combo sweeps remain for reference.
"""

from __future__ import annotations

from jambandnerd.models.experiment import ExperimentConfig

# ── Historical HP sweep (V3 base) ─────────────────────────────────────────────

BILLY_HP_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="hp_leaves15",
        description="num_leaves=15 (lower capacity)",
        param_overrides={"num_leaves": 15},
    ),
    ExperimentConfig(
        slug="hp_leaves63",
        description="num_leaves=63 (higher capacity)",
        param_overrides={"num_leaves": 63},
    ),
    ExperimentConfig(
        slug="hp_leaves127",
        description="num_leaves=127 (aggressive capacity increase)",
        param_overrides={"num_leaves": 127},
    ),
    ExperimentConfig(
        slug="hp_lr003",
        description="learning_rate=0.03 (slower learning)",
        param_overrides={"learning_rate": 0.03},
    ),
    ExperimentConfig(
        slug="hp_lr007",
        description="learning_rate=0.07 (faster learning)",
        param_overrides={"learning_rate": 0.07},
    ),
    ExperimentConfig(
        slug="hp_lr010",
        description="learning_rate=0.10 (aggressive learning rate)",
        param_overrides={"learning_rate": 0.10},
    ),
    ExperimentConfig(
        slug="hp_rounds100",
        description="num_boost_round=100 (fewer rounds)",
        round_overrides=100,
    ),
    ExperimentConfig(
        slug="hp_rounds300",
        description="num_boost_round=300 (more rounds)",
        round_overrides=300,
    ),
    ExperimentConfig(
        slug="hp_rounds500",
        description="num_boost_round=500 (aggressive round count)",
        round_overrides=500,
    ),
    ExperimentConfig(
        slug="hp_minleaf3",
        description="min_data_in_leaf=3 (less leaf regularization)",
        param_overrides={"min_data_in_leaf": 3},
    ),
    ExperimentConfig(
        slug="hp_minleaf10",
        description="min_data_in_leaf=10 (more leaf regularization)",
        param_overrides={"min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="hp_minleaf20",
        description="min_data_in_leaf=20 (heavy leaf regularization)",
        param_overrides={"min_data_in_leaf": 20},
    ),
    ExperimentConfig(
        slug="hp_lambda01",
        description="reg_lambda=0.1 (L2 regularization)",
        param_overrides={"reg_lambda": 0.1},
    ),
]

# ── Historical combo sweep (V3 base) ──────────────────────────────────────────

BILLY_COMBO_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="combo_leaves15_lr003",
        description="num_leaves=15 + learning_rate=0.03",
        param_overrides={"num_leaves": 15, "learning_rate": 0.03},
    ),
    ExperimentConfig(
        slug="combo_leaves15_lambda01",
        description="num_leaves=15 + reg_lambda=0.1",
        param_overrides={"num_leaves": 15, "reg_lambda": 0.1},
    ),
    ExperimentConfig(
        slug="combo_leaves15_minleaf10",
        description="num_leaves=15 + min_data_in_leaf=10",
        param_overrides={"num_leaves": 15, "min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_leaves15_lr003_lambda01",
        description="num_leaves=15 + lr=0.03 + reg_lambda=0.1",
        param_overrides={
            "num_leaves": 15,
            "learning_rate": 0.03,
            "reg_lambda": 0.1,
        },
    ),
    ExperimentConfig(
        slug="combo_leaves15_lr003_minleaf10",
        description="num_leaves=15 + lr=0.03 + min_data_in_leaf=10",
        param_overrides={
            "num_leaves": 15,
            "learning_rate": 0.03,
            "min_data_in_leaf": 10,
        },
    ),
    ExperimentConfig(
        slug="combo_leaves15_lr003_lambda01_minleaf10",
        description="num_leaves=15 + lr=0.03 + lambda=0.1 + minleaf=10",
        param_overrides={
            "num_leaves": 15,
            "learning_rate": 0.03,
            "reg_lambda": 0.1,
            "min_data_in_leaf": 10,
        },
    ),
]

# ── Feature sweep (V10 base) ──────────────────────────────────────────────────

BILLY_V10_FEATURE_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="feat_plays_past_year",
        description="Add plays_past_year (trailing 365-day play count)",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastV10PlaysPastYear",
    ),
    ExperimentConfig(
        slug="feat_long_rotation",
        description="Add plays_past_100 + longer-window rotation pressure",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastV10LongRotation",
    ),
    ExperimentConfig(
        slug="feat_v5_features",
        description="V5 25-feature set (gap_percentile, debut recency, calendar gap, set dist)",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastPredictorV5",
    ),
]

# ── Window / early-stopping sweep (V10 base) ──────────────────────────────────

BILLY_V10_WINDOW_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="window_early_stop",
        description="V10 + 500 rounds + 25-round per-show early stopping",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastV10EarlyStop",
    ),
    ExperimentConfig(
        slug="window_full_history",
        description="V10 + full-history training (no 75-show cap)",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastV10FullHistory",
    ),
    ExperimentConfig(
        slug="window_150",
        description="V10 + 150-show training window (2x default)",
        predictor_path="jambandnerd.models.billy.fast_predictor.BillyFastV10Window150",
    ),
]

# ── HP sweep (V10 base) ───────────────────────────────────────────────────────

BILLY_V10_HP_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="hp_lr003_r500",
        description="learning_rate=0.03 + rounds=500 (slower, more rounds from V10)",
        param_overrides={"learning_rate": 0.03},
        round_overrides=500,
    ),
    ExperimentConfig(
        slug="hp_lambda01",
        description="reg_lambda=0.1 (L2 regularization from V10 base)",
        param_overrides={"reg_lambda": 0.1},
    ),
    ExperimentConfig(
        slug="hp_leaves7",
        description="num_leaves=7 (even lower capacity than V10's 15)",
        param_overrides={"num_leaves": 7},
    ),
    ExperimentConfig(
        slug="hp_leaves31_r500",
        description="num_leaves=31 + rounds=500 (test if V10 over-regularized)",
        param_overrides={"num_leaves": 31},
        round_overrides=500,
    ),
]

# ── Full sweep index ──────────────────────────────────────────────────────────

BILLY_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "hp_sweep": BILLY_HP_SWEEP,
    "combo_sweep": BILLY_COMBO_SWEEP,
    "feature_sweep": BILLY_V10_FEATURE_SWEEP,
    "window_sweep": BILLY_V10_WINDOW_SWEEP,
    "hp_v10_sweep": BILLY_V10_HP_SWEEP,
}
