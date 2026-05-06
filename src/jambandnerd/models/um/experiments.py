"""Umphrey's McGee experiment sweep configs.

Base incumbent: UMFastPredictor (PhishFast V2 arch, 16 features, 100-show
window, dual=0.323). Zero UM-specific optimization has been done.
"""

from __future__ import annotations

from jambandnerd.models.experiment import ExperimentConfig

UM_HP_SWEEP: list[ExperimentConfig] = [
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

UM_COMBO_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="combo_lambda01_leaves15",
        description="reg_lambda=0.1 + num_leaves=15",
        param_overrides={"reg_lambda": 0.1, "num_leaves": 15},
    ),
    ExperimentConfig(
        slug="combo_lambda01_minleaf10",
        description="reg_lambda=0.1 + min_data_in_leaf=10",
        param_overrides={"reg_lambda": 0.1, "min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_leaves15_minleaf10",
        description="num_leaves=15 + min_data_in_leaf=10",
        param_overrides={"num_leaves": 15, "min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_lambda01_leaves15_minleaf10",
        description="reg_lambda=0.1 + num_leaves=15 + min_data_in_leaf=10",
        param_overrides={
            "reg_lambda": 0.1,
            "num_leaves": 15,
            "min_data_in_leaf": 10,
        },
    ),
    ExperimentConfig(
        slug="combo_lambda01_leaves15_lr007",
        description="reg_lambda=0.1 + num_leaves=15 + learning_rate=0.07",
        param_overrides={
            "reg_lambda": 0.1,
            "num_leaves": 15,
            "learning_rate": 0.07,
        },
    ),
    ExperimentConfig(
        slug="combo_all",
        description="reg_lambda=0.1 + leaves=15 + minleaf=10 + lr=0.07",
        param_overrides={
            "reg_lambda": 0.1,
            "num_leaves": 15,
            "min_data_in_leaf": 10,
            "learning_rate": 0.07,
        },
    ),
]

UM_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "hp_sweep": UM_HP_SWEEP,
    "combo_sweep": UM_COMBO_SWEEP,
}
