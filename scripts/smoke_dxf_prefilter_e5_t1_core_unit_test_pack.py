#!/usr/bin/env python3
"""DXF Prefilter E5-T1 -- structural smoke for the core unit test pack.

Deterministic structural checks (no runtime DXF execution):
1. The core unit test pack file exists.
2. All T1->T6 service imports are present.
3. The _run_pipeline T1->T6 chain helper is defined.
4. pytest.importorskip("ezdxf") guard is present (explicit dependency truth).
5. All minimum V1 scenario test functions are present.
6. No route / UI / persistence scope tokens are opened.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PACK_PATH = ROOT / "tests" / "test_dxf_preflight_core_unit_pack.py"

EXPECTED_IMPORTS = [
    "from api.services.dxf_preflight_inspect import inspect_dxf_source",
    "from api.services.dxf_preflight_role_resolver import resolve_dxf_roles",
    "from api.services.dxf_preflight_gap_repair import repair_dxf_gaps",
    "from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours",
    "from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf",
    "from api.services.dxf_preflight_acceptance_gate import",
]

EZDXF_GUARD = 'pytest.importorskip("ezdxf")'

PIPELINE_HELPER = "def _run_pipeline("

EXPECTED_SCENARIOS = [
    "def test_simple_closed_outer_accepted(",
    "def test_outer_plus_inner_accepted(",
    "def test_small_gap_repaired(",
    "def test_gap_over_threshold_lenient(",
    "def test_gap_over_threshold_strict(",
    "def test_duplicate_contour_deduped_accepted(",
    "def test_ambiguous_gap_partner_lenient(",
    "def test_ambiguous_gap_partner_strict(",
    "def test_conflicting_layer_color_lenient_not_accepted(",
    "def test_conflicting_layer_color_strict_rejected(",
]

FORBIDDEN_TOKENS = [
    "db_insert",
    "upload_trigger",
    "api/routes",
    "from api.routes",
    "frontend",
    "DxfIntakePage",
    "preflight_runs_table",
]


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(f"FAIL: {message}")


def check_file_exists() -> None:
    _assert(PACK_PATH.is_file(), f"core unit test pack file missing: {PACK_PATH}")
    print(f"  [OK] pack file exists: {PACK_PATH.relative_to(ROOT)}")


def check_content(content: str) -> None:
    # T1->T6 service imports
    for token in EXPECTED_IMPORTS:
        _assert(token in content, f"missing import: {token!r}")
    print(f"  [OK] all T1->T6 service imports present ({len(EXPECTED_IMPORTS)} checked)")

    # ezdxf dependency guard
    _assert(EZDXF_GUARD in content, f"missing ezdxf guard: {EZDXF_GUARD!r}")
    print(f"  [OK] ezdxf dependency guard present: {EZDXF_GUARD!r}")

    # T1->T6 chain helper
    _assert(PIPELINE_HELPER in content, f"missing pipeline helper: {PIPELINE_HELPER!r}")
    print(f"  [OK] _run_pipeline T1->T6 chain helper defined")

    # Minimum scenario functions
    for scenario in EXPECTED_SCENARIOS:
        _assert(scenario in content, f"missing scenario: {scenario!r}")
    print(f"  [OK] all {len(EXPECTED_SCENARIOS)} scenario test functions present")

    # Scope boundary: no route/UI/persistence tokens
    for forbidden in FORBIDDEN_TOKENS:
        _assert(
            forbidden not in content,
            f"forbidden scope token found: {forbidden!r}",
        )
    print(f"  [OK] no route/UI/persistence scope tokens ({len(FORBIDDEN_TOKENS)} checked)")

    # strict vs lenient truth: both modes covered
    _assert("strict_mode" in content, "strict_mode not referenced in pack")
    _assert("preflight_review_required" in content, "preflight_review_required not asserted")
    _assert("preflight_rejected" in content, "preflight_rejected not asserted")
    print("  [OK] strict vs lenient truth: both outcome types asserted")

    # ezdxf dependency explicitly declared (not hidden)
    _assert(
        "T5/T6 require real DXF write/read via ezdxf" in content
        or "ezdxf" in content,
        "ezdxf dependency truth not documented in pack",
    )
    print("  [OK] ezdxf dependency truth documented")

    # Cross-step assertions present (not just acceptance_outcome)
    for layer_key in [
        "inspect",
        "role",
        "gap",
        "dedupe",
        "writer",
        "gate",
    ]:
        _assert(
            f'r["{layer_key}"]' in content,
            f"missing cross-step assertion for stage: {layer_key!r}",
        )
    print("  [OK] cross-step assertions present for all 6 pipeline stages")


def main() -> None:
    print("=== smoke_dxf_prefilter_e5_t1_core_unit_test_pack ===")
    print()

    check_file_exists()

    content = PACK_PATH.read_text(encoding="utf-8")
    check_content(content)

    print()
    print("All checks passed.")


if __name__ == "__main__":
    main()
