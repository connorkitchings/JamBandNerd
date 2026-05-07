"""Widespread Panic experiment sweep configs.

Base incumbent: WSPFastPredictor V2 (19 features: 16 PhishFast V2 +
long-rotation; lr=0.03, rounds=700; dual=0.448).
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

# ── Full sweep index ──────────────────────────────────────────────────────────

WSP_SWEEPS: dict[str, list[ExperimentConfig]] = {
    "candidate_sweep": WSP_CANDIDATE_SWEEP,
    "hp_sweep": WSP_HP_SWEEP,
    "feature_sweep": WSP_FEATURE_SWEEP,
}
