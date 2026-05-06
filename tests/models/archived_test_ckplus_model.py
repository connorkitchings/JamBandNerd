from datetime import date

import pandas as pd
import pytest
from src.jambandnerd.models.ckplus.model import CKPlusPredictor

from src.jambandnerd.transformations.gaps import ModelData


class TestCKPlusPredictor:
    @pytest.fixture
    def predictor(self):
        return CKPlusPredictor(band="phish", alpha=0.5, min_plays_threshold=1)

    @pytest.fixture
    def mock_model_data(self):
        # Create a mock master_feature_set
        # song A: played recently, small gap
        # song B: played long ago, large gap, large avg gap
        features = pd.DataFrame(
            [
                {
                    "song_name": "Song A",
                    "times_played": 10,
                    "last_played_index": 95,
                    "last_played_date": date(2023, 1, 1),
                    "avg_gap": 5.0,
                    "std_gap": 1.0,
                },
                {
                    "song_name": "Song B",
                    "times_played": 20,
                    "last_played_index": 50,
                    "last_played_date": date(2022, 1, 1),
                    "avg_gap": 10.0,
                    "std_gap": 2.0,
                },
            ]
        )

        return ModelData(
            historical_plays=pd.DataFrame(),  # Not used by CK+ directly
            master_feature_set=features,
            reference_date=date(2023, 1, 10),
            reference_index=100,
            recently_played_songs=[],
            diagnostics={},
        )

    def test_predict_returns_sorted_predictions(self, predictor, mock_model_data):
        # Act
        predictions = predictor.predict(mock_model_data, top_k=2)

        # Assert
        assert len(predictions) == 2
        # Song B should have a larger gap (100 - 50 = 50) vs Song A (100 - 95 = 5).
        # Song B gap ratio: 50 / 10 = 5.0
        # Song A gap ratio: 5 / 5 = 1.0
        # Song B should be ranked higher due to higher gap ratio/score
        assert predictions[0].song_name == "Song B"
        assert predictions[1].song_name == "Song A"

    def test_predict_filters_min_plays(self, mock_model_data):
        # Arrange
        predictor = CKPlusPredictor(band="phish", min_plays_threshold=15)

        # Act
        predictions = predictor.predict(mock_model_data)

        # Assert
        # Song A has 10 plays, Song B has 20. Only Song B should remain.
        assert len(predictions) == 1
        assert predictions[0].song_name == "Song B"

    def test_score_row_calculation(self, predictor):
        # Arrange
        row = pd.Series(
            {"times_played": 10, "std_gap": 1.0, "gap_ratio": 2.0, "gap_z_score": 1.0}
        )

        # Act
        score = predictor._score_row(row)

        # Assert
        # reliability = min(1, 10/1) * (1 / (1 + 1)) = 1 * 0.5 = 0.5
        # s = 0.5 * 2.0 + (1 - 0.5) * 1.0 = 1.0 + 0.5 = 1.5
        # score = 1.5 * 0.5 = 0.75
        assert score == 0.75
