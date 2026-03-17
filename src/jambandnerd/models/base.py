"""Abstract base classes for prediction models.

Note: This base class defines the minimum interface that all prediction models
must implement. The actual accuracy calculation is handled externally by
the src.jambandnerd.models.accuracy module for consistency across models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

from ..transformations.gaps import ModelData

# Type aliases for clarity
PredictionResult = Union[List[Any], tuple[List[Any], Dict[str, Any]]]


class PredictionModel(ABC):
    """Abstract base class for prediction models.

    Each model should implement its own prediction format that best
    represents the insights from its algorithm (e.g., frequency-based,
    gap-based, etc.).

    Accuracy calculation is handled externally by the accuracy module
    to ensure consistency across all models.
    """

    def train(self, data: ModelData) -> None:
        """Train the model with historical data.

        Note: Statistical models may not require explicit training.
        This method can be a no-op for such models.
        """
        pass

    @abstractmethod
    def predict(self, model_data: ModelData, top_k: int = 50) -> PredictionResult:
        """Generate next song predictions.

        Args:
            model_data: Standardized data container with historical plays,
                       feature set, and context information
            top_k: Number of top predictions to return

        Returns:
            Model-specific prediction results. May be a list of predictions
            or a tuple of (predictions, diagnostics).
        """
        pass
