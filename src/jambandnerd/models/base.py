"""Abstract base classes for prediction models."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

# Placeholder for a standardized data object
StandardizedData = Dict[str, Any]
Prediction = Dict[str, Any]
AccuracyMetrics = Dict[str, Any]

class PredictionModel(ABC):
    """Abstract base class for prediction models."""

    @abstractmethod
    def train(self, data: StandardizedData) -> None:
        """Train the model with historical data."""
        pass

    @abstractmethod
    def predict(self, current_setlist: List[str], context: Dict[str, Any]) -> List[Prediction]:
        """Generate next song predictions."""
        pass

    @abstractmethod
    def calculate_accuracy(self, predictions: List[Prediction], actual_songs: List[str]) -> AccuracyMetrics:
        """Calculate the accuracy of the predictions."""
        pass
