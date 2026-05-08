"""Widespread Panic experiment sweep configs.

Base incumbent: WSPFastPredictor V2 (19 features: 16 PhishFast V2 +
long-rotation; lr=0.03, rounds=700; dual=0.448, F1@25=0.3248).
"""

from __future__ import annotations

from jambandnerd.models.experiment import ExperimentConfig

# ── Candidate sweep ───────────────────────────────────────────────────────────

WSP_CANDIDATE_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="cand_recent100",
        description="Candidate pruning: recent=100 (narrower recent window)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastCandidateRecent100",
    ),
    ExperimentConfig(
        slug="cand_recent200",
        description="Candidate pruning: recent=200 (wider recent window)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastCandidateRecent200",
    ),
    ExperimentConfig(
        slug="cand_recent250",
        description="Candidate pruning: recent=250 (widest recent window)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastCandidateRecent250",
    ),
    ExperimentConfig(
        slug="cand_career50",
        description="Candidate pruning: career=50 (narrower career cap)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastCandidateCareer50",
    ),
    ExperimentConfig(
        slug="cand_career150",
        description="Candidate pruning: career=150 (wider career cap)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastCandidateCareer150",
    ),
]

# ── HP (hyperparameter) sweep ─────────────────────────────────────────────────

WSP_HP_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="hp_leaves15",
        description="num_leaves=15 (lower capacity, reduce overfit risk)",
        param_overrides={"num_leaves": 15},
    ),
    ExperimentConfig(
        slug="hp_leaves63",
        description="num_leaves=63 (higher capacity)",
        param_overrides={"num_leaves": 63},
    ),
    ExperimentConfig(
        slug="hp_minleaf10",
        description="min_data_in_leaf=10 (stronger regularization)",
        param_overrides={"min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="hp_minleaf20",
        description="min_data_in_leaf=20 (heavier regularization)",
        param_overrides={"min_data_in_leaf": 20},
    ),
    ExperimentConfig(
        slug="hp_lambda01",
        description="reg_lambda=0.1 (L2 regularization)",
        param_overrides={"reg_lambda": 0.1},
    ),
    ExperimentConfig(
        slug="hp_lr003_r700",
        description="learning_rate=0.03, rounds=700 (slower, more rounds)",
        param_overrides={"learning_rate": 0.03},
        round_overrides=700,
    ),
]

# ── Feature sweep ─────────────────────────────────────────────────────────────

WSP_FEATURE_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="feat_plays_past_year",
        description="Add plays_past_year (Notebook's main recency signal) to 19-feature V2 set",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastPlaysPastYear",
    ),
    ExperimentConfig(
        slug="feat_notebook_rank",
        description="Add notebook_rank_score (normalized Notebook-style heuristic rank)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastNotebookRank",
    ),
    ExperimentConfig(
        slug="feat_venue_run",
        description="Add same-venue run prior-play candidate features",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastVenueRun",
    ),
]

_WSP_BASE = "jambandnerd.models.wsp.fast_predictor.WSPFastPredictor"

WSP_COMBO_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="combo_v2_lambda01",
        description="reg_lambda=0.1 on V2 incumbent",
        base_predictor_path=_WSP_BASE,
        param_overrides={"reg_lambda": 0.1},
    ),
    ExperimentConfig(
        slug="combo_v2_minleaf10",
        description="min_data_in_leaf=10 on V2 incumbent",
        base_predictor_path=_WSP_BASE,
        param_overrides={"min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_v2_minleaf20",
        description="min_data_in_leaf=20 on V2 incumbent",
        base_predictor_path=_WSP_BASE,
        param_overrides={"min_data_in_leaf": 20},
    ),
    ExperimentConfig(
        slug="combo_v2_leaves15",
        description="num_leaves=15 on V2 incumbent",
        base_predictor_path=_WSP_BASE,
        param_overrides={"num_leaves": 15},
    ),
    ExperimentConfig(
        slug="combo_v2_lambda01_minleaf10",
        description="reg_lambda=0.1 + min_data_in_leaf=10 on V2 incumbent",
        base_predictor_path=_WSP_BASE,
        param_overrides={"reg_lambda": 0.1, "min_data_in_leaf": 10},
    ),
    ExperimentConfig(
        slug="combo_v2_lambda01_leaves15",
        description="reg_lambda=0.1 + num_leaves=15 on V2 incumbent",
        base_predictor_path=_WSP_BASE,
        param_overrides={"reg_lambda": 0.1, "num_leaves": 15},
    ),
]

WSP_ES_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="es_patience50",
        description="early_stopping_rounds=50 (2x current patience)",
        base_predictor_path=_WSP_BASE,
        attr_overrides={"_EARLY_STOPPING_ROUNDS": 50},
    ),
    ExperimentConfig(
        slug="es_val10",
        description="validation_fraction=0.1 (smaller val set)",
        base_predictor_path=_WSP_BASE,
        attr_overrides={"_VALIDATION_FRACTION": 0.1},
    ),
    ExperimentConfig(
        slug="es_val10_pat50",
        description="validation_fraction=0.1 + early_stopping_rounds=50",
        base_predictor_path=_WSP_BASE,
        attr_overrides={"_VALIDATION_FRACTION": 0.1, "_EARLY_STOPPING_ROUNDS": 50},
    ),
    ExperimentConfig(
        slug="es_none_r50",
        description="no early stopping, fixed 50 rounds",
        base_predictor_path=_WSP_BASE,
        attr_overrides={"_EARLY_STOPPING_ROUNDS": None},
        round_overrides=50,
    ),
    ExperimentConfig(
        slug="es_none_r100",
        description="no early stopping, fixed 100 rounds",
        base_predictor_path=_WSP_BASE,
        attr_overrides={"_EARLY_STOPPING_ROUNDS": None},
        round_overrides=100,
    ),
    ExperimentConfig(
        slug="es_none_r200",
        description="no early stopping, fixed 200 rounds",
        base_predictor_path=_WSP_BASE,
        attr_overrides={"_EARLY_STOPPING_ROUNDS": None},
        round_overrides=200,
    ),
]

_ES_NONE = {"_EARLY_STOPPING_ROUNDS": None}

WSP_GAP_DECOUPLED_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="gd_default",
        description="gap_percentile + gap_vs_median (21 feats, default ES)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastGapDecoupled",
    ),
    ExperimentConfig(
        slug="gd_fr50",
        description="gap decoupled (21 feats, fixed 50 rounds)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastGapDecoupled",
        attr_overrides=_ES_NONE,
        round_overrides=50,
    ),
    ExperimentConfig(
        slug="gd_clean_fr50",
        description="gap decoupled clean (19 feats, no coupled, fixed 50 rounds)",
        predictor_path="jambandnerd.models.wsp.fast_predictor.WSPFastGapDecoupledClean",
        attr_overrides=_ES_NONE,
        round_overrides=50,
    ),
]

WSP_FIXED_ROUND_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="fr_r30",
        description="no ES, fixed 30 rounds",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        round_overrides=30,
    ),
    ExperimentConfig(
        slug="fr_r40",
        description="no ES, fixed 40 rounds",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        round_overrides=40,
    ),
    ExperimentConfig(
        slug="fr_r50",
        description="no ES, fixed 50 rounds (confirm es_none_r50)",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        round_overrides=50,
    ),
    ExperimentConfig(
        slug="fr_r40_lr05",
        description="no ES, fixed 40 rounds, lr=0.05",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        param_overrides={"learning_rate": 0.05},
        round_overrides=40,
    ),
    ExperimentConfig(
        slug="fr_r50_lr05",
        description="no ES, fixed 50 rounds, lr=0.05",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        param_overrides={"learning_rate": 0.05},
        round_overrides=50,
    ),
    ExperimentConfig(
        slug="fr_r40_lr05_lam01",
        description="no ES, fixed 40 rounds, lr=0.05, lambda=0.1",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        param_overrides={"learning_rate": 0.05, "reg_lambda": 0.1},
        round_overrides=40,
    ),
    ExperimentConfig(
        slug="fr_r50_lr05_lam01",
        description="no ES, fixed 50 rounds, lr=0.05, lambda=0.1",
        base_predictor_path=_WSP_BASE,
        attr_overrides=_ES_NONE,
        param_overrides={"learning_rate": 0.05, "reg_lambda": 0.1},
        round_overrides=50,
    ),
]

_WSP_VENUE_RUN = "jambandnerd.models.wsp.fast_predictor.WSPFastVenueRun"

WSP_VENUE_RUN_SWEEP: list[ExperimentConfig] = [
    ExperimentConfig(
        slug="vr_default",
        description="venue-run features (22 feats, default ES)",
        predictor_path=_WSP_VENUE_RUN,
    ),
    ExperimentConfig(
        slug="vr_fr50",
        description="venue-run features (22 feats, fixed 50 rounds)",
        predictor_path=_WSP_VENUE_RUN,
        attr_overrides=_ES_NONE,
        round_overrides=50,
    ),
    ExperimentConfig(
        slug="vr_fr50_lam01",
        description="venue-run features (22 feats, fixed 50 rounds, lambda=0.1)",
        predictor_path=_WSP_VENUE_RUN,
        attr_overrides=_ES_NONE,
        param_overrides={"reg_lambda": 0.1},
        round_overrides=50,
    ),
]

# ── Full sweep index ──────────────────────────────────────────────────────────

WSP_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "candidate_sweep": WSP_CANDIDATE_SWEEP,
    "hp_sweep": WSP_HP_SWEEP,
    "feature_sweep": WSP_FEATURE_SWEEP,
    "combo_sweep": WSP_COMBO_SWEEP,
    "es_sweep": WSP_ES_SWEEP,
    "fixed_round_sweep": WSP_FIXED_ROUND_SWEEP,
    "gap_decoupled_sweep": WSP_GAP_DECOUPLED_SWEEP,
    "venue_run_sweep": WSP_VENUE_RUN_SWEEP,
}
