"""CK+ prediction model package.

Implements a sophisticated gap-based statistical predictor that ranks songs
by how overdue they are, using historical show-to-show gaps, z-score
calculations, and reliability scaling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import CKPlusPrediction, CKPlusPredictor

__all__ = [
    "CKPlusPredictor",
    "CKPlusPrediction",
    "model",
]
