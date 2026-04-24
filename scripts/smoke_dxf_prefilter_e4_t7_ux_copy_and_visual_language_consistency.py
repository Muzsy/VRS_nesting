#!/usr/bin/env python3
"""DXF Prefilter E4-T7 structural smoke.

Deterministic structural checks (no runtime backend/UI execution):
1. Presentation module (dxfIntakePresentation.ts) exists with TONE, INTAKE_COPY, and badge helpers.
2. DxfIntakePage imports from dxfIntakePresentation (not re-defining badge helpers inline).
3. Status / next-step / tech-note copy layers are separated in the review overlay.
4. Diagnostics overlay uses read-only snapshot title (distinct from review overlay title).
5. Badge tone mapping uses TONE constants — no ad-hoc indigo repair badge.
6. T4 diagnostics drawer, T5 review flow, T6 create-part flow functional tokens remain present.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE_PAGE = ROOT / "frontend" / "src" / "pages" / "DxfIntakePage.tsx"
PRESENTATION = ROOT / "frontend" / "src" / "lib" / "dxfIntakePresentation.ts"
TYPES_TS = ROOT / "frontend" / "src" / "lib" / "types.ts"


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
    print("=== smoke_dxf_prefilter_e4_t7_ux_copy_and_visual_language_consistency ===")

    for path in (INTAKE_PAGE, PRESENTATION, TYPES_TS):
        _check_file_exists(path)

    intake_src = INTAKE_PAGE.read_text(encoding="utf-8")
    pres_src = PRESENTATION.read_text(encoding="utf-8")

    # 1) Presentation module: TONE, INTAKE_COPY, and all badge helpers present
    _contains_all(
        pres_src,
        [
            "export const TONE = {",
            "success:",
            "attention:",
            "blocked:",
            "queued:",
            "neutral:",
            "export const INTAKE_COPY = {",
            "export function runStatusBadge(",
            "export function acceptanceOutcomeBadge(",
            "export function issueCountBadge(",
            "export function repairCountBadge(",
            "export function recommendedNextStep(",
            "export function partCreationReadinessBadge(",
        ],
        label="presentation-module",
    )
    print("  [OK] dxfIntakePresentation.ts: TONE + INTAKE_COPY + badge helpers present")

    # 2) Status / next-step / tech-note copy separation in presentation module
    _contains_all(
        pres_src,
        [
            # Three distinct copy layers documented
            "status",
            "next step",
            "tech note",
            # Guidance copy (actionable)
            "guidance_title:",
            "guidance_body:",
            # Tech note copy (not actionable)
            "tech_note_title:",
            "tech_note_body:",
            # Overlay titles are distinct (TypeScript unquoted keys)
            'overlay_title: "Review required"',
            'overlay_title: "Preflight diagnostics"',
            'overlay_subtitle: "Read-only snapshot',
            'overlay_subtitle: "This file has ambiguous geometry',
        ],
        label="copy-layer-separation",
    )
    print("  [OK] status / next-step / tech-note copy layers separated in presentation module")

    # 3) DxfIntakePage imports from presentation module (not re-defining helpers inline)
    _contains_all(
        intake_src,
        [
            'from "../lib/dxfIntakePresentation"',
            "INTAKE_COPY",
            "runStatusBadge",
            "acceptanceOutcomeBadge",
            "issueCountBadge",
            "repairCountBadge",
            "recommendedNextStep",
            "partCreationReadinessBadge",
        ],
        label="page-imports-presentation",
    )
    print("  [OK] DxfIntakePage imports from dxfIntakePresentation — no inline badge re-definitions")

    # 4) Old inline badge function definitions are gone from the page
    _contains_none(
        intake_src,
        [
            "function formatRunStatusBadge(",
            "function formatAcceptanceOutcomeBadge(",
            "function formatIssueCountBadge(",
            "function formatRepairCountBadge(",
            "function formatRecommendedActionLabel(",
            "function formatPartCreationReadiness(",
            # Ad-hoc indigo repair badge is gone
            "bg-indigo-100 text-indigo-800",
        ],
        label="removed-inline-helpers",
    )
    print("  [OK] Inline badge helpers removed from page — no ad-hoc indigo repair badge")

    # 5) Diagnostics overlay uses distinct read-only snapshot title
    _contains_all(
        intake_src,
        [
            "INTAKE_COPY.diagnostics.overlay_title",
            "INTAKE_COPY.diagnostics.overlay_subtitle",
            "INTAKE_COPY.diagnostics.section_source",
            "INTAKE_COPY.diagnostics.section_issues",
            "INTAKE_COPY.diagnostics.section_repairs",
            "INTAKE_COPY.diagnostics.section_acceptance",
            "INTAKE_COPY.diagnostics.section_artifacts",
        ],
        label="diagnostics-copy-tokens",
    )
    print("  [OK] Diagnostics drawer uses INTAKE_COPY.diagnostics copy layer")

    # 6) Review overlay uses distinct guidance + tech note structure
    _contains_all(
        intake_src,
        [
            "INTAKE_COPY.review.overlay_title",
            "INTAKE_COPY.review.overlay_subtitle",
            "INTAKE_COPY.review.guidance_title",
            "INTAKE_COPY.review.guidance_body",
            "INTAKE_COPY.review.tech_note_title",
            "INTAKE_COPY.review.tech_note_body",
            "INTAKE_COPY.review.cta_open_diagnostics",
            "INTAKE_COPY.review.cta_upload_replacement",
            "INTAKE_COPY.review.section_replace",
        ],
        label="review-copy-tokens",
    )
    print("  [OK] Review overlay uses INTAKE_COPY.review copy layer with guidance+tech-note split")

    # 7) Accepted files -> parts section uses INTAKE_COPY
    _contains_all(
        intake_src,
        [
            "INTAKE_COPY.acceptedParts.title",
            "INTAKE_COPY.acceptedParts.helper",
            "INTAKE_COPY.acceptedParts.empty",
            "INTAKE_COPY.acceptedParts.cta_create",
            "INTAKE_COPY.acceptedParts.cta_creating",
        ],
        label="accepted-parts-copy-tokens",
    )
    print("  [OK] Accepted files -> parts section uses INTAKE_COPY.acceptedParts")

    # 8) T4 diagnostics drawer functional tokens remain (no regression)
    _contains_all(
        intake_src,
        [
            "setSelectedDiagnosticsFileId",
            "selectedDiagnosticsFile && selectedDiagnostics",
            "INTAKE_COPY.runs.cta_view_diagnostics",
        ],
        label="t4-diagnostics-regression-guard",
    )
    print("  [OK] T4 diagnostics drawer functional tokens present")

    # 9) T5 conditional review modal functional tokens remain (no regression)
    _contains_all(
        intake_src,
        [
            "canOpenConditionalReviewModal",
            "openConditionalReviewModal",
            "closeConditionalReviewModal",
            "INTAKE_COPY.runs.cta_open_review",
            "handleReviewReplacementUpload",
        ],
        label="t5-review-modal-regression-guard",
    )
    print("  [OK] T5 conditional review modal functional tokens present")

    # 10) T6 accepted files -> parts create-part flow remains (no regression)
    _contains_all(
        intake_src,
        [
            "const acceptedFilesForParts = useMemo(",
            'projection?.acceptance_outcome === "accepted_for_import"',
            "handleCreatePart(file)",
            "await api.createProjectPart(",
            "function canCreatePartFromAcceptedFile(file: ProjectFile): boolean",
            "!projection.part_creation_ready || !projection.geometry_revision_id",
        ],
        label="t6-create-part-regression-guard",
    )
    print("  [OK] T6 accepted files -> parts create-part flow tokens present")

    print("All checks passed.")


if __name__ == "__main__":
    main()
