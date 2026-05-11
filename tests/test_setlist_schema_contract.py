from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "supabase/migrations/20260511_denormalize_setlist_prediction_songs.sql"
)


def test_setlist_prediction_songs_projection_metadata_migration():
    sql = MIGRATION.read_text()

    for column in (
        "target_show_date date",
        "reference_date date",
        "generated_at timestamptz",
        "top_k integer",
    ):
        assert column in sql


def test_setlist_site_lookup_indexes_are_declared():
    sql = MIGRATION.read_text()

    assert "setlist_predictions_band_target_date_generated_idx" in sql
    assert "setlist_results_band_target_date_idx" in sql
    assert "setlist_prediction_songs_site_lookup_idx" in sql
