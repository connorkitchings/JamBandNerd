from __future__ import annotations

from scripts import evaluate_deal_model as module


def test_generate_report_emits_registry_aligned_promotion_gate(monkeypatch):
    monkeypatch.setattr(
        module,
        "generate_comparison_report",
        lambda **kwargs: {
            "candidate_model": {"slug": "deal", "version": "deal_v2"},
            "windows": {
                "last_3": {
                    "metrics_by_band": {
                        "goose": {
                            "deal": {
                                "shows_evaluated": 3,
                                "metrics": {"k10": {"hit_rate": 0.4}},
                            }
                        }
                    },
                    "cross_band_summary": {
                        "deal": {"metrics": {"k10": {"hit_rate": 0.4}}},
                        "ckplus": {"metrics": {"k10": {"hit_rate": 0.35}}},
                        "notebook": {"metrics": {"k10": {"hit_rate": 0.32}}},
                    },
                    "deltas": {},
                    "promotion_gate": {
                        "candidate_model": "deal",
                        "candidate_model_version": "deal_v2",
                        "passes": True,
                    },
                }
            },
        },
    )
    monkeypatch.setattr(module, "load_legacy_reference", lambda: {"deal": 0.3})

    report = module.generate_report("goose", 3)

    assert report["candidate_model"]["slug"] == "deal"
    assert report["comparison_window"]["shows"] == 3
    assert set(report["comparison_window"]["metrics"].keys()) == {"deal"}
    assert report["promotion_gate"]["candidate_model"] == "deal"
    assert report["promotion_gate"]["candidate_model_version"] == "deal_v2"
    assert report["promotion_gate"]["enabled_for_web"] is False
    assert report["promotion_gate"]["beats_legacy_deal_by_0_05"] is True
    assert report["promotion_gate"]["matches_or_beats_ckplus"] is True
