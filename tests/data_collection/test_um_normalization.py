import pandas as pd

from src.jambandnerd.data_collection.um.normalizer import normalize_setlists
from src.jambandnerd.data_collection.utils import attach_source_hash_column


class TestUmNormalization:
    def test_attach_source_hash(self):
        df = pd.DataFrame([{"song_name": "Pay the Snucka", "show_id": "1"}])
        result = attach_source_hash_column(df)
        assert "source_hash" in result.columns
        assert len(result["source_hash"].iloc[0]) == 64  # SHA-256 hex

    def test_attach_source_hash_empty(self):
        df = pd.DataFrame()
        result = attach_source_hash_column(df)
        assert result.empty

    def test_normalize_setlists_coerces_numeric_columns(self):
        df = pd.DataFrame(
            [
                {
                    "song_name": "Pay the Snucka",
                    "show_id": "1",
                    "set_sequence": "1",
                    "song_position": "3",
                    "show_position": "3",
                }
            ]
        )
        result = normalize_setlists(df)
        assert result["set_sequence"].dtype.name == "Int64"
        assert result["song_position"].dtype.name == "Int64"
        assert "source_hash" in result.columns

    def test_normalize_setlists_does_not_add_legacy_set_number(self):
        df = pd.DataFrame(
            [
                {
                    "song_name": "S",
                    "show_id": "1",
                    "set_label": "Set 1",
                    "set_sequence": "1",
                    "song_position": "1",
                }
            ]
        )
        result = normalize_setlists(df)
        assert "set_number" not in result.columns
        assert result["set_sequence"].iloc[0] == 1

    def test_normalize_setlists_handles_missing_optional_set_sequence(self):
        df = pd.DataFrame(
            [
                {
                    "song_name": "S",
                    "show_id": "1",
                    "set_label": "Encore",
                    "song_position": "1",
                }
            ]
        )
        result = normalize_setlists(df)
        assert "set_sequence" not in result.columns
        assert bool(result["encore"].iloc[0]) is True
