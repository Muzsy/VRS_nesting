#!/usr/bin/env python3
"""DXF Prefilter E4-T6 structural smoke.

Deterministic structural checks (no runtime backend/UI execution):
1. Files route exposes optional include_part_creation_projection and readiness projection.
2. Frontend type/API boundary contains part-creation projection + createProjectPart helper.
3. DxfIntakePage renders a dedicated accepted-files -> parts block.
4. Create-part flow is guarded by accepted+ready state, with explicit pending/not-eligible cues.
5. T4 diagnostics drawer and T5 conditional review modal tokens remain present.
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
    print("=== smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow ===")

    for path in (INTAKE_PAGE, API_TS, TYPES_TS, FILES_ROUTE):
        _check_file_exists(path)

    intake_src = INTAKE_PAGE.read_text(encoding="utf-8")
    api_src = API_TS.read_text(encoding="utf-8")
    types_src = TYPES_TS.read_text(encoding="utf-8")
    route_src = FILES_ROUTE.read_text(encoding="utf-8")

    # 1) Backend optional projection on existing files route (no new accepted-files endpoint)
    _contains_all(
        route_src,
        [
            "include_part_creation_projection: bool = Query(default=False)",
            "def _build_latest_part_creation_projection(",
            '"readiness_reason": readiness_reason,',
            '"part_creation_ready": part_creation_ready,',
            "_fetch_latest_geometry_revision_by_file_id(",
            "_fetch_existing_part_projection_by_geometry_revision_id(",
        ],
        label="backend-projection",
    )
    _assert("accepted-files" not in route_src, "unexpected accepted-files endpoint token found in files route")
    print("  [OK] backend files route optional projection tokens present")

    # 2) Frontend type/API boundary
    _contains_all(
        types_src,
        [
            "ProjectFileLatestPartCreationProjection",
            "latest_part_creation_projection?: ProjectFileLatestPartCreationProjection | null;",
            "ProjectPartCreateRequest",
            "ProjectPartCreateResponse",
        ],
        label="types-boundary",
    )
    _contains_all(
        api_src,
        [
            "normalizeLatestPartCreationProjection(",
            "include_part_creation_projection",
            "createProjectPart(",
            "`/projects/${projectId}/parts`",
        ],
        label="api-boundary",
    )
    print("  [OK] frontend type/API boundary tokens present")

    # 3) Dedicated accepted-files -> parts block on DxfIntakePage
    _contains_all(
        intake_src,
        [
            "Accepted files -&gt; parts",
            "const acceptedFilesForParts = useMemo(",
            'projection?.acceptance_outcome === "accepted_for_import"',
            "handleCreatePart(file)",
            "await api.createProjectPart(",
        ],
        label="accepted-files-block",
    )
    print("  [OK] accepted files -> parts section tokens present")

    # 4) Guard rails: accepted+ready only, explicit pending/not-eligible messaging
    _contains_all(
        intake_src,
        [
            "function canCreatePartFromAcceptedFile(file: ProjectFile): boolean",
            "!projection.part_creation_ready || !projection.geometry_revision_id",
            "accepted_geometry_import_pending",
            "not_eligible_review_required",
            "not_eligible_rejected",
            "Geometry import pending. Refresh after import.",
            "const disableCreate = !canCreate || partCreationInFlightFileId !== null;",
        ],
        label="create-guards",
    )
    print("  [OK] create-part guard tokens present")

    # 5) T4/T5 no regression markers
    _contains_all(
        intake_src,
        [
            "View diagnostics",
            "Diagnostics",
            "Conditional review modal",
            "Open review",
            "Open full diagnostics drawer",
        ],
        label="t4-t5-regression-guard",
    )
    print("  [OK] T4 diagnostics + T5 review modal tokens remain present")

    print("All checks passed.")


if __name__ == "__main__":
    main()
