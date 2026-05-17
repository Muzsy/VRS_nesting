from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.experiments import lv8_phase1_cache_usage_matrix as m


# ---------------------------------------------------------------------------
# Existing T10 tests (unchanged — regression guard)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# T10B new tests
# ---------------------------------------------------------------------------

def test_lv8_time_limit_sec_passed_to_lv8_family(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """LV8-prefix families receive lv8_time_limit_sec, not the default time_limit_sec."""
    fixture = m.FixtureSpec(
        family_id="lv8_276",
        fixture_path=m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json",
        required=True,
        enabled=True,
    )
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: [fixture])

    captured: dict[str, int] = {}

    def fake_run_harness(**kwargs: Any) -> tuple[dict[str, Any], int]:
        captured[kwargs["label"]] = kwargs["time_limit_sec"]
        return (
            {
                "out_dir": str(tmp_path),
                "return_code": 0,
                "valid": True,
                "valid_polygon_gate": True,
                "valid_quantity_gate": True,
                "timed_out": False,
                "engine_stats": {
                    "available": True,
                    "normalized": {
                        "nfp_cache_hit_count": 5,
                        "nfp_cache_miss_count": 5,
                        "nfp_cache_entries_end": 5,
                        "nfp_cache_clear_all_events": 0,
                        "nfp_cache_peak_entries": 5,
                        "nfp_compute_count": 5,
                    },
                },
            },
            0,
        )

    monkeypatch.setattr(m, "_run_harness", fake_run_harness)
    m.run_matrix(
        tmp_path,
        time_limit_sec=30,
        seed=1,
        include_lv8_179="0",
        profiles=["q"],
        lv8_time_limit_sec=120,
    )

    assert "lv8_276:q" in captured
    assert captured["lv8_276:q"] == 120, "LV8 family must receive lv8_time_limit_sec"


def test_sa_guard_gets_default_time_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """sa_guard family receives time_limit_sec, not lv8_time_limit_sec."""
    specs = [
        m.FixtureSpec("lv8_276", m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json", required=True, enabled=True),
        m.FixtureSpec("sa_guard", m.REPO_ROOT / "poc/nesting_engine/f2_4_sa_quality_fixture_v2.json", required=True, enabled=True),
    ]
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: specs)

    captured: dict[str, int] = {}

    def fake_run_harness(**kwargs: Any) -> tuple[dict[str, Any], int]:
        family = kwargs["label"].split(":")[0]
        captured[family] = kwargs["time_limit_sec"]
        return (
            {
                "out_dir": str(tmp_path),
                "return_code": 0,
                "valid": True,
                "valid_polygon_gate": True,
                "timed_out": False,
                "engine_stats": {
                    "available": True,
                    "normalized": {"nfp_cache_hit_count": 5, "nfp_cache_miss_count": 5, "nfp_cache_clear_all_events": 0},
                },
            },
            0,
        )

    monkeypatch.setattr(m, "_run_harness", fake_run_harness)
    m.run_matrix(
        tmp_path,
        time_limit_sec=30,
        seed=1,
        include_lv8_179="0",
        profiles=["q"],
        lv8_time_limit_sec=120,
    )

    assert captured.get("lv8_276") == 120
    assert captured.get("sa_guard") == 30


def test_phase2a_unblocked_false_when_lv8_stats_missing_default() -> None:
    """Without advisory flag, missing LV8 stats → phase2a_unblocked=False."""
    rows = [
        {
            "row_type": "engine_run",
            "family_id": "lv8_276",
            "engine_stats_available": False,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": None,
            "timed_out": True,
        },
        {
            "row_type": "engine_run",
            "family_id": "sa_guard",
            "engine_stats_available": True,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": 0,
        },
    ]
    decision = m.compute_decision(
        rows,
        required_families={"lv8_276", "sa_guard"},
        blocked_reason=None,
        # allow_lv8_timeout_without_stats=False by default
    )
    assert decision["phase2a_unblocked"] is False
    assert decision["phase2a_ready_source"] == "blocked"
    assert decision["lv8_stats_available"] is False
    assert decision["sa_guard_stats_available"] is True


def test_phase2a_unblocked_via_smoke_advisory_path() -> None:
    """Advisory path: stats_required_families={"sa_guard"} + allow flag → phase2a_unblocked."""
    rows = [
        {
            "row_type": "engine_run",
            "family_id": "lv8_276",
            "engine_stats_available": False,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": None,
        },
        {
            "row_type": "engine_run",
            "family_id": "sa_guard",
            "engine_stats_available": True,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": 0,
        },
    ]
    decision = m.compute_decision(
        rows,
        required_families={"lv8_276", "sa_guard"},
        blocked_reason=None,
        stats_required_families={"sa_guard"},
        allow_lv8_timeout_without_stats=True,
    )
    assert decision["phase2a_unblocked"] is True
    assert decision["phase2a_ready_source"] == "smoke_stats_plus_lv8_advisory"
    assert decision["sa_guard_stats_available"] is True
    assert decision["lv8_stats_available"] is False


def test_stats_required_families_full_set_blocks_advisory() -> None:
    """When stats_required_families == required_families, advisory path is unreachable."""
    rows = [
        {
            "row_type": "engine_run",
            "family_id": "lv8_276",
            "engine_stats_available": False,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": None,
        },
        {
            "row_type": "engine_run",
            "family_id": "sa_guard",
            "engine_stats_available": True,
            "valid_polygon_gate": True,
            "nfp_cache_clear_all_events": 0,
        },
    ]
    # Default stats_required_families = all required → advisory needs both → fails
    decision = m.compute_decision(
        rows,
        required_families={"lv8_276", "sa_guard"},
        blocked_reason=None,
        # stats_required_families=None → defaults to required_families
        allow_lv8_timeout_without_stats=True,
    )
    assert decision["phase2a_unblocked"] is False
    assert decision["phase2a_ready_source"] == "blocked"


def test_lv8_timeout_row_preserved_in_matrix_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Timeout rows are not silently dropped from the matrix output."""
    fixture = m.FixtureSpec(
        family_id="lv8_276",
        fixture_path=m.REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json",
        required=True,
        enabled=True,
    )
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: [fixture])

    def fake_run_harness(**_kwargs: Any) -> tuple[dict[str, Any], int]:
        return (
            {
                "return_code": 2,
                "timed_out": True,
                "valid": False,
                "valid_polygon_gate": True,
                "engine_stats": {
                    "available": False,
                    "normalized": None,
                    "parse_error": "missing_stats_line",
                },
            },
            2,
        )

    monkeypatch.setattr(m, "_run_harness", fake_run_harness)
    matrix, code = m.run_matrix(
        tmp_path,
        time_limit_sec=60,
        seed=1,
        include_lv8_179="0",
        profiles=["q"],
    )

    engine_rows = [r for r in matrix["rows"] if r.get("row_type") == "engine_run"]
    assert len(engine_rows) == 1, "Timeout row must not be dropped"
    assert engine_rows[0]["timed_out"] is True
    assert engine_rows[0]["engine_stats_available"] is False
    assert code == 3
    # Decision fields must reflect the blocker explicitly
    assert matrix["lv8_stats_available"] is False
    assert matrix["phase2a_unblocked"] is False


def test_lv8_and_sa_guard_stats_available_fields() -> None:
    """lv8_stats_available and sa_guard_stats_available are reported separately."""
    rows = [
        {"row_type": "engine_run", "family_id": "lv8_276", "engine_stats_available": False, "valid_polygon_gate": True, "nfp_cache_clear_all_events": None},
        {"row_type": "engine_run", "family_id": "lv8_179", "engine_stats_available": False, "valid_polygon_gate": True, "nfp_cache_clear_all_events": None},
        {"row_type": "engine_run", "family_id": "sa_guard", "engine_stats_available": True, "valid_polygon_gate": True, "nfp_cache_clear_all_events": 0},
    ]
    decision = m.compute_decision(rows, required_families={"lv8_276", "sa_guard"}, blocked_reason=None)
    assert decision["lv8_stats_available"] is False
    assert decision["sa_guard_stats_available"] is True


def test_full_stats_path_when_all_available() -> None:
    """When all required families have stats, full_required_stats path is taken."""
    rows = [
        {"row_type": "engine_run", "family_id": "lv8_276", "engine_stats_available": True, "valid_polygon_gate": True, "nfp_cache_clear_all_events": 0},
        {"row_type": "engine_run", "family_id": "sa_guard", "engine_stats_available": True, "valid_polygon_gate": True, "nfp_cache_clear_all_events": 0},
    ]
    decision = m.compute_decision(rows, required_families={"lv8_276", "sa_guard"}, blocked_reason=None)
    assert decision["phase2a_unblocked"] is True
    assert decision["phase2a_ready_source"] == "full_required_stats"
    assert decision["lv8_stats_available"] is True
    assert decision["sa_guard_stats_available"] is True


def test_matrix_json_includes_lv8_time_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Matrix JSON records the effective lv8_time_limit_sec for auditability."""
    fixture = m.FixtureSpec(
        family_id="lv8_179",
        fixture_path=m.REPO_ROOT / "tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json",
        required=False,
        enabled=False,
        missing_reason="fixture_missing",
    )
    monkeypatch.setattr(m, "build_fixture_specs", lambda _mode: [fixture])
    matrix, _ = m.run_matrix(
        tmp_path,
        time_limit_sec=60,
        seed=1,
        include_lv8_179="0",
        profiles=["q"],
        lv8_time_limit_sec=180,
    )
    assert matrix["time_limit_sec"] == 60
    assert matrix["lv8_time_limit_sec"] == 180
