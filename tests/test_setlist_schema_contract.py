from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "supabase/migrations/20260511_denormalize_setlist_prediction_songs.sql"
)
ACCURACY_TARGET_DATE_MIGRATION = (
    ROOT / "supabase/migrations/20260512_add_target_show_date_to_setlist_accuracy.sql"
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


def test_setlist_accuracy_target_show_date_migration():
    sql = ACCURACY_TARGET_DATE_MIGRATION.read_text()

    assert "add column if not exists target_show_date date" in sql
    assert "target_show_date = show_date" in sql
    assert "alter column target_show_date set not null" in sql
    assert "setlist_accuracy_band_target_date_idx" in sql
