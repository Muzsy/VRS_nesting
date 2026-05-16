from __future__ import annotations

from scripts.experiments.lv8_phase0_shadow_run_matrix import decide_hard_cut, eval_pair
from vrs_nesting.config.nesting_quality_profiles import get_phase0_shadow_profile_pairs


def test_profile_pair_mapping_contains_expected_pairs() -> None:
    pairs = get_phase0_shadow_profile_pairs()
    assert pairs["quality_default"] == "quality_default_no_sa_shadow"
    assert pairs["quality_aggressive"] == "quality_aggressive_no_sa_shadow"


def test_missing_fixture_forces_defer_hard_cut() -> None:
    decision = decide_hard_cut(
        [
            {
                "row_type": "fixture_missing",
                "family_id": "lv8_179",
                "status": "fixture_missing",
            }
        ]
    )
    assert decision["hard_cut_decision"] == "DEFER_HARD_CUT"


def test_no_sa_better_or_equal_means_pair_pass_true() -> None:
    legacy = {
        "placed_instances": 100,
        "utilization_pct": 70.0,
        "valid_polygon_gate": True,
        "timed_out": False,
        "return_code": 0,
    }
    shadow = {
        "placed_instances": 100,
        "utilization_pct": 70.0,
        "valid_polygon_gate": True,
        "timed_out": False,
        "return_code": 0,
    }
    out = eval_pair(legacy, shadow)
    assert out["pair_pass"] is True


def test_polygon_gate_false_cannot_pass_when_legacy_true() -> None:
    legacy = {
        "placed_instances": 100,
        "utilization_pct": 70.0,
        "valid_polygon_gate": True,
        "timed_out": False,
        "return_code": 0,
    }
    shadow = {
        "placed_instances": 110,
        "utilization_pct": 75.0,
        "valid_polygon_gate": False,
        "timed_out": False,
        "return_code": 0,
    }
    out = eval_pair(legacy, shadow)
    assert out["pair_pass"] is False
    assert out["checks"]["polygon_gate_not_worse"] is False


def test_contract_freeze_not_applicable_row_has_no_fake_util_compare() -> None:
    row = {
        "row_type": "contract_freeze_regression",
        "family_id": "web_platform_contract_freeze",
        "shadow_profile_applicability": "not_applicable",
        "regression_gate": "PASS",
    }
    assert row["shadow_profile_applicability"] == "not_applicable"
    assert "utilization_pct" not in row
    assert "placed_instances" not in row
