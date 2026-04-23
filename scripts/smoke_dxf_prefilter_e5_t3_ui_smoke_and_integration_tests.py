#!/usr/bin/env python3
"""DXF Prefilter E5-T3 -- structural smoke for DXF Intake UI smoke / integration pack.

Deterministic structural checks (no Playwright execution):
1. Playwright spec file exists.
2. Spec references DxfIntakePage route and installMockApi harness.
3. rules_profile_snapshot_jsonb finalize payload capture is asserted in spec.
4. Accepted scenario (accepted_for_import + Ready for next step + drawer blocks) present.
5. Non-accepted scenario (preflight_review_required) present.
6. mockApi.ts harness has latest_preflight_summary/diagnostics + finalizedBodies extensions.
7. Forbidden scope guard: no real backend, no new endpoint, no accepted->parts scope.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC_PATH = ROOT / "frontend" / "e2e" / "dxf_prefilter_e5_t3_dxf_intake.spec.ts"
MOCK_API_PATH = ROOT / "frontend" / "e2e" / "support" / "mockApi.ts"

SPEC_REQUIRED_TOKENS = [
    "installMockApi",
    "dxf-intake",
    "rules_profile_snapshot_jsonb",
    "accepted_for_import",
    "preflight_review_required",
    "Ready for next step",
    "View diagnostics",
    "Source inventory",
    "Role mapping",
    "finalizedBodies",
]

MOCK_REQUIRED_TOKENS = [
    "latest_preflight_summary",
    "latest_preflight_diagnostics",
    "finalizedBodies",
]

SPEC_FORBIDDEN_TOKENS = [
    "BackgroundTasks",
    "TestClient",
    "@testing-library",
    "cypress",
    "run_preflight_for_upload",
    "create_parts",
    "CreateParts",
]


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(f"FAIL: {message}")


def check_spec_exists() -> None:
    _assert(SPEC_PATH.is_file(), f"Playwright spec missing: {SPEC_PATH}")
    print(f"  [OK] spec file exists: {SPEC_PATH.relative_to(ROOT)}")


def check_mock_api_exists() -> None:
    _assert(MOCK_API_PATH.is_file(), f"mockApi.ts missing: {MOCK_API_PATH}")
    print(f"  [OK] mockApi.ts exists: {MOCK_API_PATH.relative_to(ROOT)}")


def check_spec_content(content: str) -> None:
    for token in SPEC_REQUIRED_TOKENS:
        _assert(token in content, f"spec missing required token: {token!r}")
    print(f"  [OK] spec required tokens present ({len(SPEC_REQUIRED_TOKENS)} checked)")

    for forbidden in SPEC_FORBIDDEN_TOKENS:
        _assert(forbidden not in content, f"spec contains forbidden scope token: {forbidden!r}")
    print(f"  [OK] spec scope guard: no forbidden tokens ({len(SPEC_FORBIDDEN_TOKENS)} checked)")

    # Verify all 6 diagnostics drawer block headings are asserted
    drawer_blocks = ["Source inventory", "Role mapping", "Issues", "Repairs", "Acceptance", "Artifacts"]
    for block in drawer_blocks:
        _assert(block in content, f"spec missing diagnostics drawer block assertion: {block!r}")
    print(f"  [OK] diagnostics drawer: all 6 block headings asserted ({drawer_blocks})")

    # Verify settings bridge assertions present
    _assert("strict_mode" in content, "spec missing strict_mode bridge assertion")
    _assert("max_gap_close_mm" in content, "spec missing max_gap_close_mm bridge assertion")
    print("  [OK] settings -> finalize payload bridge assertions present")

    # Verify advisory only (no mutation)
    _assert('"Ready for next step"' in content or "'Ready for next step'" in content,
            "spec missing Ready for next step advisory assertion")
    _assert("not.toBeVisible" in content, "spec missing not.toBeVisible guard for non-accepted advisory")
    print("  [OK] advisory-only accepted state asserted (Ready for next step + not.toBeVisible guard)")


def check_mock_api_content(content: str) -> None:
    for token in MOCK_REQUIRED_TOKENS:
        _assert(token in content, f"mockApi.ts missing required token: {token!r}")
    print(f"  [OK] mockApi.ts extensions present ({len(MOCK_REQUIRED_TOKENS)} checked)")


def main() -> None:
    print("=== smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests ===")
    print()

    check_spec_exists()
    check_mock_api_exists()

    spec_content = SPEC_PATH.read_text(encoding="utf-8")
    check_spec_content(spec_content)

    mock_content = MOCK_API_PATH.read_text(encoding="utf-8")
    check_mock_api_content(mock_content)

    print()
    print("All checks passed.")


if __name__ == "__main__":
    main()
