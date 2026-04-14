from datetime import date, timedelta

import pandas as pd
import pytest

from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.transformations.gaps import ModelData


class TestNotebookPredictor:
    @pytest.fixture
    def model_data(self):
        # Create mock data
        today = date(2024, 1, 1)

        # Historical plays
        # Song A: Played 5 times in last year
        # Song B: Played 2 times in last year
        # Song C: Played 0 times in last year (but exists)
        # Song D: Played recently (gap 1)

        plays_data = []
        # Song A plays
        for i in range(5):
            plays_data.append(
                {
                    "song_name": "Song A",
                    "show_date": today - timedelta(days=10 * i),
                    "show_index": 100 - i,
                }
            )

        # Song B plays
        for i in range(2):
            plays_data.append(
                {
                    "song_name": "Song B",
                    "show_date": today - timedelta(days=20 * i),
                    "show_index": 90
                    - i,  # Changed from 100-i to 90-i to ensure gap > 3
                }
            )

        # Song D play (recent)
        plays_data.append(
            {
                "song_name": "Song D",
                "show_date": today - timedelta(days=1),
                "show_index": 100,
            }
        )

        historical_plays = pd.DataFrame(plays_data)

        # Master feature set
        features_data = [
            {
                "song_name": "Song A",
                "last_played_date": today - timedelta(days=10),
                "last_played_index": 96,
            },
            {
                "song_name": "Song B",
                "last_played_date": today - timedelta(days=20),
                "last_played_index": 90,
            },
            {
                "song_name": "Song C",
                "last_played_date": today - timedelta(days=400),
                "last_played_index": 50,
            },  # Old
            {
                "song_name": "Song D",
                "last_played_date": today - timedelta(days=1),
                "last_played_index": 100,
            },
        ]
        master_feature_set = pd.DataFrame(features_data)

        return ModelData(
            master_feature_set=master_feature_set,
            historical_plays=historical_plays,
            reference_index=101,
            reference_date=today,
            recently_played_songs={"Song D"},  # Song D is recent
            diagnostics={},
        )

    def test_predict_ranks_by_plays_past_year(self, model_data):
        predictor = NotebookPredictor()
        predictions, _ = predictor.predict(model_data)

        # Song A (5 plays) should be before Song B (2 plays)
        assert len(predictions) >= 2
        assert predictions[0].song_name == "Song A"
        assert predictions[0].plays_past_year == 5
        assert predictions[1].song_name == "Song B"
        assert predictions[1].plays_past_year == 2

        song_a = next(
            prediction for prediction in predictions if prediction.song_name == "Song A"
        )
        song_b = next(
            prediction for prediction in predictions if prediction.song_name == "Song B"
        )
        assert song_a.current_gap == 4
        assert song_b.current_gap == 10

    def test_predict_excludes_recent_songs(self, model_data):
        predictor = NotebookPredictor()
        predictions, _ = predictor.predict(model_data)

        # Song D should be excluded
        song_names = [p.song_name for p in predictions]
        assert "Song D" not in song_names

    def test_predict_excludes_songs_not_in_window(self, model_data):
        predictor = NotebookPredictor()
        predictions, _ = predictor.predict(model_data)

        # Song C (played > 1 year ago) should be excluded because it has 0 plays in window
        # The logic is: inner join with plays_past_year_count.
        # If plays_past_year is 0 (not in group), it's dropped.
        song_names = [p.song_name for p in predictions]
        assert "Song C" not in song_names

    def test_predict_tiebreaker_gap(self, model_data):
        # Modify data to have tie in plays
        # Add Song E with 5 plays but larger gap than Song A

        today = date(2024, 1, 1)
        new_plays = []
        for i in range(5):
            new_plays.append(
                {
                    "song_name": "Song E",
                    "show_date": today - timedelta(days=10 * i),
                    "show_index": 100 - i,
                }
            )

        model_data.historical_plays = pd.concat(
            [model_data.historical_plays, pd.DataFrame(new_plays)]
        )

        # Song A last played index 96 (gap = 101 - 96 - 1 = 4)
        # Song E last played index 90 (gap = 101 - 90 - 1 = 10)
        new_feature = pd.DataFrame(
            [
                {
                    "song_name": "Song E",
                    "last_played_date": today - timedelta(days=10),
                    "last_played_index": 90,
                }
            ]
        )
        model_data.master_feature_set = pd.concat(
            [model_data.master_feature_set, new_feature]
        )

        predictor = NotebookPredictor()
        predictions, _ = predictor.predict(model_data)

        # Song E (gap 10) should be before Song A (gap 4)
        assert predictions[0].song_name == "Song E"
        assert predictions[1].song_name == "Song A"

    def test_wsp_filtering(self, model_data):
        # Add 'Drums' to data
        today = date(2024, 1, 1)
        new_plays = [{"song_name": "Drums", "show_date": today, "show_index": 100}]
        model_data.historical_plays = pd.concat(
            [model_data.historical_plays, pd.DataFrame(new_plays)]
        )

        new_feature = pd.DataFrame(
            [
                {
                    "song_name": "Drums",
                    "last_played_date": today,
                    "last_played_index": 100,
                }
            ]
        )
        model_data.master_feature_set = pd.concat(
            [model_data.master_feature_set, new_feature]
        )

        predictor = NotebookPredictor(band="wsp")
        predictions, _ = predictor.predict(model_data)

        song_names = [p.song_name for p in predictions]
        assert "Drums" not in song_names
