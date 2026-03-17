"""Tests for prediction models."""

import pytest

from jambandnerd.models.base import PredictionModel


class TestPredictionModelBase:
    """Tests for the abstract PredictionModel base class."""

    def test_prediction_model_is_abstract(self):
        """Test that PredictionModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PredictionModel()

    def test_prediction_model_interface(self):
        """Test that PredictionModel defines the expected interface."""
        # Check that the abstract methods exist
        assert hasattr(PredictionModel, "train")
        assert hasattr(PredictionModel, "predict")

        # Check that they are marked as abstract methods
        assert PredictionModel.predict.__isabstractmethod__
        # train is not abstract (has default implementation)


class MockPredictionModel(PredictionModel):
    """Mock implementation of PredictionModel for testing."""

    def __init__(self):
        self.trained = False

    def train(self, data):
        """Mock training method."""
        self.trained = True

    def predict(self, current_setlist, context):
        """Mock prediction method."""
        if not self.trained:
            raise RuntimeError("Model must be trained before making predictions")

        return [
            {"song": "Test Song 1", "probability": 0.6},
            {"song": "Test Song 2", "probability": 0.4},
        ]

    def calculate_accuracy(self, predictions, actual_songs):
        """Mock accuracy calculation method."""
        return {
            "top_1_accuracy": 0.75,
            "top_3_accuracy": 0.90,
            "mean_reciprocal_rank": 0.82,
        }


class TestMockPredictionModel:
    """Tests for the mock PredictionModel implementation."""

    def test_mock_model_instantiation(self):
        """Test that the mock model can be instantiated."""
        model = MockPredictionModel()
        assert isinstance(model, PredictionModel)
        assert not model.trained

    def test_train_model(self):
        """Test the train method."""
        model = MockPredictionModel()
        mock_data = {"shows": [], "setlists": []}

        model.train(mock_data)

        assert model.trained

    def test_predict_without_training(self):
        """Test that prediction fails without training."""
        model = MockPredictionModel()

        with pytest.raises(RuntimeError, match="Model must be trained"):
            model.predict([], {})

    def test_predict_after_training(self):
        """Test the predict method after training."""
        model = MockPredictionModel()
        model.train({})

        predictions = model.predict(["Current Song"], {"venue": "Test Venue"})

        assert len(predictions) == 2
        assert predictions[0]["song"] == "Test Song 1"
        assert predictions[0]["probability"] == 0.6
        assert predictions[1]["song"] == "Test Song 2"
        assert predictions[1]["probability"] == 0.4

    def test_calculate_accuracy(self):
        """Test the calculate_accuracy method."""
        model = MockPredictionModel()
        mock_predictions = [
            {"song": "Song A", "probability": 0.5},
            {"song": "Song B", "probability": 0.3},
        ]
        mock_actual = ["Song A", "Song C"]

        accuracy = model.calculate_accuracy(mock_predictions, mock_actual)

        assert accuracy["top_1_accuracy"] == 0.75
        assert accuracy["top_3_accuracy"] == 0.90
        assert accuracy["mean_reciprocal_rank"] == 0.82
