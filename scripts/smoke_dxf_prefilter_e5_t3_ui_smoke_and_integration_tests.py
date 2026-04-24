#!/usr/bin/env python3
"""DXF Prefilter E5-T3 structural smoke.

Deterministic structural checks (no runtime backend/UI execution):
1. Playwright spec file exists for the DxfIntakePage UI flows.
2. Spec uses installMockApi harness (not ad-hoc page.route).
3. Settings -> upload finalize bridge scenario is present (rules_profile_snapshot_jsonb assertion).
4. Accepted latest run -> diagnostics drawer scenario is present with E4-T7 canonical copy.
5. Non-accepted latest run -> correct badge / advisory scenario is present with E4-T7 canonical copy.
6. Stale pre-T7 text strings are gone from spec.
7. MockApi.ts has latest_part_creation_projection field in MockFile interface.
8. No new backend endpoint, tesztframework or accepted->parts future scope invented.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "frontend" / "e2e" / "dxf_prefilter_e5_t3_dxf_intake.spec.ts"
MOCK_API = ROOT / "frontend" / "e2e" / "support" / "mockApi.ts"


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(f"FAIL: {message}")


def _check_file_exists(path: Path) -> None:
    _assert(path.is_file(), f"missing file: {path}")


def _contains_all(content: str, required: list[str], *, label: str) -> None:
    for token in required:
        _assert(token in content, f"missing {label} token: {token!r}")


def _contains_none(content: str, forbidden: list[str], *, label: str) -> None:
    for token in forbidden:
        _assert(token not in content, f"unexpected {label} token still present: {token!r}")


def main() -> None:
    print("=== smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests ===")

    for path in (SPEC, MOCK_API):
        _check_file_exists(path)

    spec_src = SPEC.read_text(encoding="utf-8")
    mock_src = MOCK_API.read_text(encoding="utf-8")

    # 1) Spec uses installMockApi harness
    _contains_all(
        spec_src,
        [
            'from "./support/mockApi"',
            "installMockApi(page)",
            "mock.state.projects.push",
            "mock.state.filesByProject",
        ],
        label="mock-harness-usage",
    )
    print("  [OK] Spec uses installMockApi harness")

    # 2) Settings -> upload finalize bridge scenario
    _contains_all(
        spec_src,
        [
            "rules_profile_snapshot_jsonb",
            "mock.state.finalizedBodies",
            'input[type="checkbox"]',
            'input[step="0.01"]',
            'input[type="file"]',
            "Upload complete. Preflight starts automatically.",
        ],
        label="settings-upload-bridge-scenario",
    )
    print("  [OK] Settings -> upload finalize bridge scenario present")

    # 3) Accepted latest run -> diagnostics drawer scenario with E4-T7 canonical copy
    _contains_all(
        spec_src,
        [
            "ACCEPTED_SUMMARY",
            "ACCEPTED_DIAGNOSTICS",
            "latest_preflight_summary: ACCEPTED_SUMMARY",
            "latest_preflight_diagnostics: ACCEPTED_DIAGNOSTICS",
            'acceptance_outcome: "accepted_for_import"',
            "View diagnostics",
            # E4-T7 canonical copy
            "Ready — proceed to part creation",
            "Preflight diagnostics",
            "Source inventory",
            "Role mapping",
            "Issues",
            "Repairs",
            "Acceptance outcome",
            "Artifacts",
        ],
        label="accepted-diagnostics-drawer-scenario",
    )
    print("  [OK] Accepted latest run -> diagnostics drawer scenario present with E4-T7 copy")

    # 4) Non-accepted (review_required) scenario with E4-T7 canonical copy
    _contains_all(
        spec_src,
        [
            "REVIEW_REQUIRED_SUMMARY",
            "REVIEW_REQUIRED_DIAGNOSTICS",
            "latest_preflight_summary: REVIEW_REQUIRED_SUMMARY",
            'acceptance_outcome: "preflight_review_required"',
            "review required",
            # E4-T7 canonical copy
            "Open review overlay to inspect issues",
        ],
        label="non-accepted-scenario",
    )
    print("  [OK] Non-accepted (review_required) scenario present with E4-T7 copy")

    # 5) Stale pre-T7 copy strings are gone
    _contains_none(
        spec_src,
        [
            '"Ready for next step"',
            '"Wait for diagnostics"',
            '{ name: "Diagnostics" }',
            '{ name: "Acceptance" }',
        ],
        label="stale-pre-t7-copy",
    )
    print("  [OK] Stale pre-T7 copy strings removed from spec")

    # 6) MockFile interface has latest_part_creation_projection
    _contains_all(
        mock_src,
        [
            "latest_part_creation_projection?: Record<string, unknown> | null;",
        ],
        label="mock-file-part-creation-projection",
    )
    print("  [OK] MockFile interface has latest_part_creation_projection field")

    # 7) No new backend endpoint or tesztframework invented
    _contains_none(
        spec_src,
        [
            "import { test } from 'vitest'",
            "import { render } from '@testing-library",
            "from 'cypress'",
            "supertest",
            "createProjectPart",
            "replaceProjectFile",
        ],
        label="no-new-scope",
    )
    print("  [OK] No new backend endpoint / tesztframework / accepted->parts scope in spec")

    print("All checks passed.")


if __name__ == "__main__":
    main()
