from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.experiments import lv8_phase1_cache_usage_matrix as m


def test_cache_hit_rate_and_total_lookups() -> None:
    summary: dict[str, Any] = {
        "out_dir": "tmp/run1",
        "engine_stats": {
            "available": True,
            "normalized": {
                "nfp_cache_hit_count": 8,
                "nfp_cache_miss_count": 2,
                "nfp_cache_entries_end": 4,
                "nfp_cache_clear_all_events": 0,
                "nfp_cache_peak_entries": 10,
                "nfp_compute_count": 2,
            },
        },
        "valid_polygon_gate": True,
        "valid_quantity_gate": True,
        "valid": True,
        "placed_instances": 12,
        "utilization_pct": 42.0,
        "runtime_sec": 1.5,
        "return_code": 0,
        "timed_out": False,
    }
    row = m._row_from_summary("lv8_276", m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json", "q", summary)
    assert row["cache_total_lookups"] == 10
    assert row["cache_hit_rate"] == pytest.approx(0.8)


def test_zero_lookup_hit_rate_is_none() -> None:
    summary: dict[str, Any] = {
        "out_dir": "tmp/run2",
        "engine_stats": {
            "available": True,
            "normalized": {
                "nfp_cache_hit_count": 0,
                "nfp_cache_miss_count": 0,
            },
        },
    }
    row = m._row_from_summary("lv8_276", m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json", "q", summary)
    assert row["cache_total_lookups"] == 0
    assert row["cache_hit_rate"] is None


def test_optional_lv8_179_missing_adds_fixture_missing_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fixture = m.FixtureSpec(
        family_id="lv8_179",
        fixture_path=m.REPO_ROOT / "tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json",
        required=False,
        enabled=False,
        missing_reason="fixture_missing",
    )
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: [fixture])
    matrix, code = m.run_matrix(tmp_path, time_limit_sec=1, seed=1, include_lv8_179="auto", profiles=["quality_default_no_sa_shadow"])

    assert code == 0
    rows = matrix["rows"]
    assert len(rows) == 1
    assert rows[0]["row_type"] == "fixture_missing"
    assert rows[0]["family_id"] == "lv8_179"
    assert rows[0]["status"] == "fixture_missing"


def test_missing_required_fixture_is_blocked_exit_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fixture = m.FixtureSpec(
        family_id="lv8_276",
        fixture_path=m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json",
        required=True,
        enabled=False,
        missing_reason="missing_fixture",
    )
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: [fixture])
    matrix, code = m.run_matrix(tmp_path, time_limit_sec=1, seed=1, include_lv8_179="auto", profiles=["quality_default_no_sa_shadow"])

    assert code == 2
    assert matrix["blocked_reason"] == "required_fixture_missing:lv8_276"
    assert matrix["phase2a_ready"] is False


def test_engine_stats_unavailable_returns_exit_3(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fixture = m.FixtureSpec(
        family_id="lv8_276",
        fixture_path=m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json",
        required=True,
        enabled=True,
        missing_reason="missing_fixture",
    )
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: [fixture])

    def fake_run_harness(**_kwargs: Any) -> tuple[dict[str, Any], int]:
        return (
            {
                "out_dir": "tmp/fake",
                "return_code": 0,
                "valid": True,
                "valid_polygon_gate": True,
                "valid_quantity_gate": True,
                "engine_stats": {"available": False, "normalized": None},
            },
            0,
        )

    monkeypatch.setattr(m, "_run_harness", fake_run_harness)
    matrix, code = m.run_matrix(tmp_path, time_limit_sec=1, seed=1, include_lv8_179="0", profiles=["quality_default_no_sa_shadow"])

    assert code == 3
    assert matrix["cache_stats_available_all_required_runs"] is False
    assert matrix["phase2a_ready"] is False


def test_clear_all_events_requires_lru_followup() -> None:
    rows = [
        {
            "row_type": "engine_run",
            "family_id": "lv8_276",
            "engine_stats_available": True,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": 1,
        }
    ]
    decision = m.compute_decision(rows, required_families={"lv8_276"}, blocked_reason=None)
    assert decision["lru_followup_required"] is True
    assert decision["phase2a_ready"] is False


def test_polygon_gate_false_forces_polygon_gate_available_false() -> None:
    rows = [
        {
            "row_type": "engine_run",
            "family_id": "lv8_276",
            "engine_stats_available": True,
            "valid_polygon_gate": False,
            "nfp_cache_clear_all_events": 0,
        }
    ]
    decision = m.compute_decision(rows, required_families={"lv8_276"}, blocked_reason=None)
    assert decision["polygon_gate_available_all_required_runs"] is False
    assert decision["phase2a_ready"] is False
