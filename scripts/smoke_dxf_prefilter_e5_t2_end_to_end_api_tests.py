#!/usr/bin/env python3
"""DXF Prefilter E5-T2 -- structural smoke for API-level end-to-end test pack.

Deterministic structural checks (no runtime API execution):
1. API E2E pack file exists.
2. Route-level chain tokens are present:
   complete_upload, BackgroundTasks, run_preflight_for_upload, list_project_files.
3. Explicit ezdxf dependency guard exists.
4. accepted / review_required / rejected scenario coverage exists.
5. Scope guard: no UI / Playwright / TestClient / new /preflight endpoint scope.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PACK_PATH = ROOT / "tests" / "test_dxf_preflight_api_end_to_end.py"

REQUIRED_TOKENS = [
    "from fastapi import BackgroundTasks",
    "from api.routes.files import FileCompleteRequest, complete_upload, list_project_files",
    "files_mod.run_preflight_for_upload",
    "include_preflight_summary=True",
    "include_preflight_diagnostics=True",
]

EZDXF_GUARD = 'pytest.importorskip("ezdxf")'

EXPECTED_SCENARIOS = [
    "def test_preflight_api_e2e_accepted_flow_persists_projection_and_triggers_geometry_import(",
    "def test_preflight_api_e2e_lenient_review_required_skips_geometry_import_and_keeps_diagnostics(",
    "def test_preflight_api_e2e_strict_rejected_skips_geometry_import_and_projects_rejected_state(",
]

FORBIDDEN_TOKENS = [
    "from fastapi.testclient import TestClient",
    "TestClient(",
    "playwright",
    "Playwright",
    "DxfIntakePage",
    "frontend/src",
    "POST /projects/{project_id}/files/{file_id}/preflight",
    "/preflight-runs",
]


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(f"FAIL: {message}")


def check_file_exists() -> None:
    _assert(PACK_PATH.is_file(), f"API E2E pack missing: {PACK_PATH}")
    print(f"  [OK] pack file exists: {PACK_PATH.relative_to(ROOT)}")


def check_content(content: str) -> None:
    for token in REQUIRED_TOKENS:
        _assert(token in content, f"missing required token: {token!r}")
    print(f"  [OK] route-level chain tokens present ({len(REQUIRED_TOKENS)} checked)")

    _assert(EZDXF_GUARD in content, f"missing ezdxf guard: {EZDXF_GUARD!r}")
    print(f"  [OK] explicit ezdxf guard present: {EZDXF_GUARD!r}")

    for scenario in EXPECTED_SCENARIOS:
        _assert(scenario in content, f"missing scenario test: {scenario!r}")
    print(f"  [OK] accepted/review_required/rejected scenarios present ({len(EXPECTED_SCENARIOS)} checked)")

    _assert("preflight_review_required" in content, "review_required outcome assertion missing")
    _assert("preflight_rejected" in content, "strict rejected outcome assertion missing")
    _assert("accepted_for_import" in content, "accepted outcome assertion missing")
    print("  [OK] outcome assertions present for all three acceptance states")

    for forbidden in FORBIDDEN_TOKENS:
        _assert(forbidden not in content, f"forbidden scope token found: {forbidden!r}")
    print(f"  [OK] no forbidden scope tokens ({len(FORBIDDEN_TOKENS)} checked)")


def main() -> None:
    print("=== smoke_dxf_prefilter_e5_t2_end_to_end_api_tests ===")
    print()

    check_file_exists()
    content = PACK_PATH.read_text(encoding="utf-8")
    check_content(content)

    print()
    print("All checks passed.")


if __name__ == "__main__":
    main()
