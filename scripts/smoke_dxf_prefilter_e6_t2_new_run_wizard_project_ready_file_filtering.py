#!/usr/bin/env python3
"""DXF Prefilter E6-T2 structural smoke.

Deterministic source-level checks only (no runtime dependencies).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_SLUG = "dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering"

NEW_RUN_PAGE = ROOT / "frontend" / "src" / "pages" / "NewRunPage.tsx"
E2E_SPEC = ROOT / "frontend" / "e2e" / f"{TASK_SLUG}.spec.ts"
CANVAS = ROOT / "canvases" / "web_platform" / f"{TASK_SLUG}.md"
YAML = ROOT / "codex" / "goals" / "canvases" / "web_platform" / f"fill_canvas_{TASK_SLUG}.yaml"
RUN_PROMPT = ROOT / "codex" / "prompts" / "web_platform" / TASK_SLUG / "run.md"

DUPLICATE_CANVAS = ROOT / "canvases" / f"{TASK_SLUG}.md"
DUPLICATE_YAML = ROOT / "codex" / "goals" / "canvases" / f"fill_canvas_{TASK_SLUG}.yaml"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(f"FAIL: {message}")


def _read(path: Path) -> str:
    _assert(path.is_file(), f"missing file: {path}")
    return path.read_text(encoding="utf-8")


def _contains_all(content: str, tokens: list[str], *, label: str) -> None:
    for token in tokens:
        _assert(token in content, f"missing {label} token: {token!r}")


def _contains_none(content: str, tokens: list[str], *, label: str) -> None:
    for token in tokens:
        _assert(token not in content, f"unexpected {label} token present: {token!r}")


def main() -> None:
    print("=== smoke_dxf_prefilter_e6_t2_new_run_wizard_project_ready_file_filtering ===")

    new_run_src = _read(NEW_RUN_PAGE)
    _contains_all(
        new_run_src,
        [
            "include_preflight_summary: true",
            "include_part_creation_projection: true",
            "function hasLinkedPartRevision(file: ProjectFile): boolean",
            "function isProjectReadyPartFile(file: ProjectFile): boolean",
            "function isRunUsableStockFile(file: ProjectFile): boolean",
            "resolveExistingPartRevisionId(file) !== null",
            "projectReadyPartFiles",
            "eligibleStockFiles",
            "No project-ready parts yet. Open DXF Intake / Project Preparation and create parts first.",
            "to={`/projects/${projectId}/dxf-intake`}",
        ],
        label="new-run-page",
    )
    _contains_none(
        new_run_src,
        [
            "fileResponse.items.find((file) => isDxfSourceFile(file)) ?? fileResponse.items[0] ?? null",
            "files.filter((file) => isDxfSourceFile(file))",
        ],
        label="legacy-step1-controls",
    )
    print("  [OK] NewRunPage uses intake-aware fetch + project-ready/eligible filtering without legacy raw-DXF controls")

    e2e_src = _read(E2E_SPEC)
    _contains_all(
        e2e_src,
        [
            "source_rejected_01.dxf",
            "source_review_01.dxf",
            "source_pending_01.dxf",
            "toHaveCount(0)",
            "Continue to parameters",
            "Selected file has no linked part revision",
        ],
        label="e2e-spec",
    )
    print("  [OK] E2E spec exists and contains rejected/review/pending exclusion assertions")

    _assert(CANVAS.is_file(), f"missing task canvas: {CANVAS}")
    _assert(YAML.is_file(), f"missing task yaml: {YAML}")
    _assert(RUN_PROMPT.is_file(), f"missing task run prompt: {RUN_PROMPT}")
    _assert(not DUPLICATE_CANVAS.exists(), f"unexpected root-level duplicate canvas: {DUPLICATE_CANVAS}")
    _assert(not DUPLICATE_YAML.exists(), f"unexpected root-level duplicate yaml: {DUPLICATE_YAML}")
    print("  [OK] task artifacts are in web_platform paths with no root-level duplicate canvas/yaml")

    print("All checks passed.")


if __name__ == "__main__":
    main()
