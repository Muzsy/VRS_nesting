#!/usr/bin/env python3
"""DXF Prefilter E4-T5 structural smoke.

Deterministic structural checks (no runtime backend/UI execution):
1. Conditional review trigger is guarded to review_required + diagnostics-present rows only.
2. Separate conditional review modal tokens exist (not just the T4 diagnostics drawer).
3. Replacement flow uses existing replace route helper + complete_upload bridge fields.
4. T4 diagnostics drawer remains present.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE_PAGE = ROOT / "frontend" / "src" / "pages" / "DxfIntakePage.tsx"
API_TS = ROOT / "frontend" / "src" / "lib" / "api.ts"
TYPES_TS = ROOT / "frontend" / "src" / "lib" / "types.ts"
FILES_ROUTE = ROOT / "api" / "routes" / "files.py"


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(f"FAIL: {message}")


def _check_file_exists(path: Path) -> None:
    _assert(path.is_file(), f"missing file: {path}")


def _contains_all(content: str, required: list[str], *, label: str) -> None:
    for token in required:
        _assert(token in content, f"missing {label} token: {token!r}")


def main() -> None:
    print("=== smoke_dxf_prefilter_e4_t5_conditional_review_modal ===")

    for path in (INTAKE_PAGE, API_TS, TYPES_TS, FILES_ROUTE):
        _check_file_exists(path)

    intake_src = INTAKE_PAGE.read_text(encoding="utf-8")
    api_src = API_TS.read_text(encoding="utf-8")
    types_src = TYPES_TS.read_text(encoding="utf-8")
    route_src = FILES_ROUTE.read_text(encoding="utf-8")

    # 1) Conditional trigger guard: review_required + diagnostics payload
    _contains_all(
        intake_src,
        [
            "canOpenConditionalReviewModal(file: ProjectFile)",
            'acceptance_outcome === "preflight_review_required" && !!file.latest_preflight_diagnostics',
            "const canOpenReview = canOpenConditionalReviewModal(file);",
            "Open review",
            "{canOpenReview ? (",
        ],
        label="conditional-trigger",
    )
    print("  [OK] conditional trigger guard tokens present")

    # 2) Separate review modal tokens + current-code disclaimer
    _contains_all(
        intake_src,
        [
            "Conditional review modal",
            "Review summary",
            "Review-required issues",
            "Remaining review-required signals",
            "What to do now",
            "persisted review decision save is not implemented yet",
            "Open full diagnostics drawer",
        ],
        label="review-modal",
    )
    print("  [OK] review modal tokens present")

    # 3) Replacement helper + finalize bridge fields
    _contains_all(
        types_src,
        [
            "ProjectFileReplaceUploadResponse",
            "replaces_file_id",
            "storage_path",
        ],
        label="types-boundary",
    )
    _contains_all(
        api_src,
        [
            "replaceProjectFile(",
            "`/projects/${projectId}/files/${fileId}/replace`",
            "replaces_file_object_id?: string | null",
        ],
        label="api-boundary",
    )
    _contains_all(
        intake_src,
        [
            "await api.replaceProjectFile(",
            "await api.completeUpload(",
            "replaces_file_object_id: signed.replaces_file_id",
            "rules_profile_snapshot_jsonb: rulesProfileSnapshot",
        ],
        label="replacement-flow",
    )
    _contains_all(
        route_src,
        [
            '@router.post("/{file_id}/replace", response_model=FileReplaceResponse)',
            "class FileReplaceResponse(BaseModel):",
            "replaces_file_id: str",
            "replaces_file_object_id: UUID | None = None",
        ],
        label="backend-route",
    )
    print("  [OK] replacement helper + finalize bridge tokens present")

    # 4) T4 diagnostics drawer still present
    _contains_all(
        intake_src,
        [
            "View diagnostics",
            "Diagnostics",
            "Source inventory",
            "Role mapping",
            "Issues",
            "Repairs",
            "Acceptance",
            "Artifacts",
        ],
        label="t4-diagnostics-drawer",
    )
    print("  [OK] T4 diagnostics drawer tokens remain present")

    print("All checks passed.")


if __name__ == "__main__":
    main()
