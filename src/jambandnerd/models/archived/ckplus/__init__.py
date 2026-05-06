"""Archived CK+ prediction model package.

This model is retired from active use. It is retained here for historical
reference and potential future analysis. The model was a gap-based statistical
predictor that ranked songs by how overdue they were.

Status: Retired (lifecycle_stage="retired", enabled_for_pipeline=False)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import CKPlusPrediction, CKPlusPredictor

__all__ = [
    "CKPlusPredictor",
    "CKPlusPrediction",
    "model",
]
