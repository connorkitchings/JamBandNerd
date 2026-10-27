from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

import jambandnerd.models.evaluation as bare_evaluation_module
import scripts.run_backtest as run_backtest_module
import src.jambandnerd.models.evaluation as evaluation_module
from scripts.common import prepare_band_data
from scripts.run_backtest import build_scored_run_records
from src.jambandnerd.models.registry import (
    build_band_predictor,
    get_band_metadata,
    get_band_serializer,
)
from src.jambandnerd.transformations.gaps import generate_model_data


def build_notebook_semantics_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    shows = pd.DataFrame(
        [
            {"show_id": "show-1", "show_date": "2024-01-01"},
            {"show_id": "show-2", "show_date": "2024-01-02"},
            {"show_id": "show-3", "show_date": "2024-01-03"},
            {"show_id": "show-4", "show_date": "2024-01-04"},
            {"show_id": "show-5", "show_date": "2024-01-05"},
            {"show_id": "show-6", "show_date": "2024-01-10"},
            {"show_id": "show-7", "show_date": "2024-01-11"},
        ]
    )
    setlists = pd.DataFrame(
        [
            {"show_id": "show-1", "song_name": "Alpha"},
            {"show_id": "show-1", "song_name": "Beta"},
            {"show_id": "show-1", "song_name": "Gamma"},
            {"show_id": "show-2", "song_name": "Alpha"},
            {"show_id": "show-2", "song_name": "Beta"},
            {"show_id": "show-2", "song_name": "Delta"},
            {"show_id": "show-3", "song_name": "Alpha"},
            {"show_id": "show-3", "song_name": "Epsilon"},
            {"show_id": "show-3", "song_name": "Zeta"},
            {"show_id": "show-4", "song_name": "Theta"},
            {"show_id": "show-4", "song_name": "Iota"},
            {"show_id": "show-4", "song_name": "Kappa"},
            {"show_id": "show-5", "song_name": "Lambda"},
            {"show_id": "show-5", "song_name": "Mu"},
            {"show_id": "show-5", "song_name": "Nu"},
            {"show_id": "show-6", "song_name": "Alpha"},
            {"show_id": "show-6", "song_name": "Beta"},
            {"show_id": "show-6", "song_name": "Sigma"},
            {"show_id": "show-7", "song_name": "Omicron"},
            {"show_id": "show-7", "song_name": "Pi"},
            {"show_id": "show-7", "song_name": "Rho"},
        ]
    )
    return prepare_band_data(shows, setlists, band="goose")


def notebook_song_names_for_reference_date(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date: date,
) -> list[str]:
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        reference_date,
        exclusion_window=3,
        band="goose",
    )
    predictor = build_band_predictor(band="goose")
    prediction_output = predictor.predict(
        model_data=model_data,
        top_k=get_band_metadata("goose").default_top_k,
    )
    predictions = (
        prediction_output[0]
        if isinstance(prediction_output, tuple)
        else prediction_output
    )
    serialized = get_band_serializer("goose")(predictions)
    return [row["song_name"] for row in serialized]


def test_backtest_rows_use_previous_day_reference_date_for_completed_show() -> None:
    shows_df, setlists_df = build_notebook_semantics_fixture()

    direct_for_prior_show = notebook_song_names_for_reference_date(
        shows_df,
        setlists_df,
        date(2024, 1, 10),
    )
    direct_for_target_show = notebook_song_names_for_reference_date(
        shows_df,
        setlists_df,
        date(2024, 1, 11),
    )

    target_shows = shows_df[shows_df["show_date"] == date(2024, 1, 11)].copy()
    scored_runs = build_scored_run_records(
        band="goose",
        shows_df=shows_df,
        sets_df=setlists_df,
        target_shows=target_shows,
        exclusion_window=3,
    )

    assert len(scored_runs) == 1
    assert scored_runs[0]["target_show_date"] == "2024-01-11"
    assert scored_runs[0]["reference_date"] == "2024-01-10"
    assert [
        row["song_name"] for row in scored_runs[0]["predictions"]
    ] == direct_for_target_show
    assert direct_for_target_show != direct_for_prior_show

    consecutive_targets = shows_df[
        shows_df["show_date"].isin([date(2024, 1, 10), date(2024, 1, 11)])
    ].copy()
    consecutive_runs = build_scored_run_records(
        band="goose",
        shows_df=shows_df,
        sets_df=setlists_df,
        target_shows=consecutive_targets,
        exclusion_window=3,
    )
    assert len(consecutive_runs) == 2
    assert consecutive_runs[0]["predictions"] != consecutive_runs[1]["predictions"]


def test_backtest_passes_target_show_context_without_target_setlist(
    monkeypatch,
) -> None:
    shows_df, setlists_df = build_notebook_semantics_fixture()
    shows_df = shows_df.copy()
    shows_df["venue_name"] = "Test Theatre"
    shows_df["city"] = "New York"
    shows_df["state"] = "NY"
    shows_df["country"] = "USA"
    target_shows = shows_df[shows_df["show_date"] == date(2024, 1, 11)].copy()
    captured: dict[str, object] = {}

    def fake_generate_model_data(*_args, **kwargs):
        context = dict(kwargs["target_show_context"])
        captured["context"] = context
        return SimpleNamespace(
            reference_date=kwargs["target_show_context"]["show_date"]
        )

    class FakePredictor:
        def train(self, model_data):
            pass

        def predict(self, **_kwargs):
            return [SimpleNamespace(song_name="Alpha")]

    monkeypatch.setattr(
        evaluation_module, "generate_model_data", fake_generate_model_data
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_band_metadata",
        lambda _band: SimpleNamespace(
            model_version="test_v1",
            default_top_k=50,
            supports_training=False,
        ),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "build_band_predictor",
        lambda *_args, **_kwargs: FakePredictor(),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_band_serializer",
        lambda _band: lambda _preds: [{"song_name": "Alpha"}],
    )

    scored_runs = build_scored_run_records(
        band="goose",
        shows_df=shows_df,
        sets_df=setlists_df,
        target_shows=target_shows,
        exclusion_window=3,
    )

    assert len(scored_runs) == 1
    assert captured["context"]["venue_name"] == "Test Theatre"
    assert captured["context"]["show_date"] == date(2024, 1, 11)
    assert "song_name" not in captured["context"]


# ---------------------------------------------------------------------------
# Evaluation cutoff: every offline harness must keep the previous night's show.
# ---------------------------------------------------------------------------

TARGET_DATE = date(2024, 1, 11)


class _StopHarness(Exception):
    pass


def _spy_cutoff(monkeypatch) -> list[date]:
    seen: list[date] = []

    def spy(shows_df, sets_df, reference_date, **_kwargs):
        seen.append(reference_date)
        raise _StopHarness()

    # Scripts import the package as both `src.jambandnerd` and `jambandnerd`.
    monkeypatch.setattr(evaluation_module, "generate_model_data", spy)
    monkeypatch.setattr(bare_evaluation_module, "generate_model_data", spy)
    return seen


def _target_shows(shows_df: pd.DataFrame) -> pd.DataFrame:
    return shows_df[shows_df["show_date"] == TARGET_DATE]


def _run_backtest_harness(shows_df, sets_df, _monkeypatch):
    with pytest.raises(RuntimeError):
        build_scored_run_records(
            band="goose",
            shows_df=shows_df,
            sets_df=sets_df,
            target_shows=_target_shows(shows_df),
            exclusion_window=3,
        )


def _run_phase_b_harness(shows_df, sets_df, monkeypatch):
    import scripts.run_phase_b_backtest as module

    monkeypatch.setattr(module, "fetch_table", lambda *_a, **_k: [{"x": 1}])
    monkeypatch.setattr(
        module, "prepare_band_data", lambda *_a, **_k: (shows_df, sets_df)
    )

    class Dummy:
        def __init__(self, **_kwargs):
            pass

    with pytest.raises(RuntimeError, match="no scored records"):
        module.run_phase_b_backtest(
            band="goose", predictor_class=Dummy, shows=1, out_dir="unused"
        )


def _run_wsp_harness(shows_df, sets_df, _monkeypatch):
    import scripts.wsp_failure_analysis as module

    row = _target_shows(shows_df).iloc[0]
    module.analyze_show(
        show_row=row,
        sets_df=sets_df,
        predictor=object(),
        shows_df=shows_df,
        recent_songs_map={},
        top_career=set(),
        song_stats={},
        show_songs_map={str(row["show_id"]): ["a", "b", "c"]},
        shows_meta={},
    )


def _run_blend_harness(shows_df, sets_df, _monkeypatch):
    import scripts.evaluate_goose_notebook_blend as module

    class Dummy:
        def __init__(self, **_kwargs):
            pass

    with pytest.raises(_StopHarness):
        module._score_target_show(
            band="goose",
            predictor_class=Dummy,
            shows_df=shows_df,
            sets_df=sets_df,
            show_row=_target_shows(shows_df).iloc[0],
        )


def _run_diagnose_harness(module_name: str):
    def run(shows_df, sets_df, _monkeypatch):
        import importlib

        module = importlib.import_module(f"scripts.{module_name}")
        with pytest.raises(RuntimeError):
            module._collect_training_frames(
                band="goose",
                predictor=object(),
                shows_df=shows_df,
                sets_df=sets_df,
                target_shows=_target_shows(shows_df),
            )

    return run


@pytest.mark.parametrize(
    "run_harness",
    [
        _run_backtest_harness,
        _run_phase_b_harness,
        _run_wsp_harness,
        _run_blend_harness,
        _run_diagnose_harness("diagnose_phase_b_features"),
        _run_diagnose_harness("diagnose_goose_features"),
    ],
)
def test_offline_harness_includes_previous_night_show_in_features(
    monkeypatch, run_harness
) -> None:
    shows_df, sets_df = build_notebook_semantics_fixture()
    seen = _spy_cutoff(monkeypatch)

    run_harness(shows_df, sets_df, monkeypatch)

    # generate_model_data keeps shows strictly before this date, so the target
    # date itself (not target - 1) keeps the 2024-01-10 show in the history.
    assert seen == [TARGET_DATE]


# ---------------------------------------------------------------------------
# run_backtest failure accounting, predictor isolation, and re-score window.
# ---------------------------------------------------------------------------


def _build_consecutive_shows(n: int, start: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    shows = pd.DataFrame(
        [
            {"show_id": f"s{i}", "show_date": (start + timedelta(days=i)).isoformat()}
            for i in range(n)
        ]
    )
    setlists = pd.DataFrame(
        [
            {"show_id": f"s{i}", "song_name": name}
            for i in range(n)
            for name in ("Alpha", "Beta", "Gamma")
        ]
    )
    return prepare_band_data(shows, setlists, band="goose")


class _RecordingPredictor:
    built = 0

    def __init__(self, skip_train_for: set[date]) -> None:
        type(self).built += 1
        self.skip_train_for = skip_train_for
        self.trained_on: date | None = None

    def train(self, model_data) -> None:
        if model_data.reference_date in self.skip_train_for:
            return  # early return, as a real train() can do
        self.trained_on = model_data.reference_date

    def predict(self, **_kwargs):
        return [SimpleNamespace(song_name=f"trained-{self.trained_on}")]


def _patch_scoring(monkeypatch, *, fail_dates=(), skip_train_for=()):
    _RecordingPredictor.built = 0

    def fake_generate(_shows, _sets, reference_date, **_kwargs):
        if reference_date in fail_dates:
            raise ValueError("boom")
        return SimpleNamespace(reference_date=reference_date)

    monkeypatch.setattr(evaluation_module, "generate_model_data", fake_generate)
    monkeypatch.setattr(
        run_backtest_module,
        "build_band_predictor",
        lambda *_a, **_k: _RecordingPredictor(set(skip_train_for)),
    )
    monkeypatch.setattr(
        run_backtest_module,
        "get_band_serializer",
        lambda _band: lambda preds: [{"song_name": p.song_name} for p in preds],
    )


def _score(shows_df, sets_df, **kwargs):
    return build_scored_run_records(
        band="goose",
        shows_df=shows_df,
        sets_df=sets_df,
        target_shows=shows_df,
        exclusion_window=3,
        **kwargs,
    )


def test_failed_show_under_threshold_is_tolerated_and_logged(
    monkeypatch, caplog
) -> None:
    shows_df, sets_df = _build_consecutive_shows(20, date(2024, 1, 1))
    _patch_scoring(monkeypatch, fail_dates={date(2024, 1, 5)})

    records = _score(shows_df, sets_df)

    assert len(records) == 19
    assert "show_id=s4" in caplog.text
    assert "boom" in caplog.text


def test_failed_shows_over_threshold_raise(monkeypatch) -> None:
    shows_df, sets_df = _build_consecutive_shows(20, date(2024, 1, 1))
    _patch_scoring(
        monkeypatch, fail_dates={date(2024, 1, 5), date(2024, 1, 6), date(2024, 1, 7)}
    )

    with pytest.raises(RuntimeError, match="3 of 20 show"):
        _score(shows_df, sets_df)


def test_any_failed_show_raises_when_results_required(monkeypatch) -> None:
    shows_df, sets_df = _build_consecutive_shows(20, date(2024, 1, 1))
    _patch_scoring(monkeypatch, fail_dates={date(2024, 1, 5)})

    with pytest.raises(RuntimeError, match="1 of 20 show"):
        _score(shows_df, sets_df, fail_on_any_error=True)


def test_early_return_train_does_not_reuse_previous_show_model(monkeypatch) -> None:
    shows_df, sets_df = _build_consecutive_shows(2, date(2024, 1, 1))
    _patch_scoring(monkeypatch, skip_train_for={date(2024, 1, 2)})

    records = _score(shows_df, sets_df)

    assert _RecordingPredictor.built == 2
    assert [r["predictions"][0]["song_name"] for r in records] == [
        "trained-2024-01-01",
        "trained-None",
    ]


def test_incremental_rescores_recent_shows_even_when_already_scored(
    monkeypatch,
) -> None:
    today = date.today()
    shows_df = pd.DataFrame(
        [
            {"show_id": "old", "show_date": today - timedelta(days=30)},
            {"show_id": "recent", "show_date": today - timedelta(days=2)},
        ]
    )
    sets_df = pd.DataFrame(
        [{"show_id": sid, "song_name": n} for sid in ("old", "recent") for n in "abc"]
    )
    captured: dict[str, list[str]] = {}

    def fake_build(**kwargs):
        captured["ids"] = kwargs["target_shows"]["show_id"].tolist()
        return []

    monkeypatch.setattr(
        run_backtest_module, "_verify_supabase_write_access", lambda: None
    )
    monkeypatch.setattr(
        run_backtest_module,
        "load_backtest_frames",
        lambda *_a, **_k: (shows_df, sets_df),
    )
    monkeypatch.setattr(run_backtest_module, "list_completed_shows", lambda s, _t: s)
    monkeypatch.setattr(run_backtest_module, "select_target_shows", lambda s, **_k: s)
    monkeypatch.setattr(
        run_backtest_module,
        "fetch_scored_target_show_keys",
        lambda *_a, **_k: {"old", "recent"},
    )
    monkeypatch.setattr(run_backtest_module, "build_scored_run_records", fake_build)

    run_backtest_module.run_backtest(
        band="goose",
        start=None,
        end=None,
        shows=2,
        exclusion_window=3,
        dry_run=True,
    )

    assert captured["ids"] == ["recent"]
