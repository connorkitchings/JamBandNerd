import pandas as pd

from src.jambandnerd.data_collection.um.normalizer import (
    attach_source_hash,
    normalize_setlists,
)


class TestUmNormalization:
    def test_attach_source_hash(self):
        df = pd.DataFrame([{"song_name": "Pay the Snucka", "show_id": "1"}])
        result = attach_source_hash(df)
        assert "source_hash" in result.columns
        assert len(result["source_hash"].iloc[0]) == 64  # SHA-256 hex

    def test_attach_source_hash_empty(self):
        df = pd.DataFrame()
        result = attach_source_hash(df)
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

    def test_normalize_setlists_adds_set_number_from_set_label(self):
        df = pd.DataFrame(
            [
                {
                    "song_name": "S",
                    "show_id": "1",
                    "set_label": "Set 1",
                    "song_position": "1",
                }
            ]
        )
        result = normalize_setlists(df)
        assert "set_number" in result.columns
        assert result["set_number"].iloc[0] == "Set 1"
