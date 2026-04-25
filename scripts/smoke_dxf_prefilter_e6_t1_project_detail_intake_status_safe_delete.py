#!/usr/bin/env python3
"""DXF Prefilter E6-T1 structural smoke.

Deterministic source-level checks only (no backend/frontend runtime required).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_SLUG = "dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete"

MIGRATION = ROOT / "supabase" / "migrations" / "20260425190000_dxf_e6_t1_file_object_soft_archive.sql"
FILES_ROUTE = ROOT / "api" / "routes" / "files.py"
PROJECT_DETAIL_PAGE = ROOT / "frontend" / "src" / "pages" / "ProjectDetailPage.tsx"
MOCK_API = ROOT / "frontend" / "e2e" / "support" / "mockApi.ts"
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
    print("=== smoke_dxf_prefilter_e6_t1_project_detail_intake_status_safe_delete ===")

    _assert("xxxxxx" not in MIGRATION.name, f"migration filename must be Supabase-timestamped, got: {MIGRATION.name}")
    _assert(
        not (ROOT / "supabase" / "migrations" / "20260425xxxxxx_dxf_e6_t1_file_object_soft_archive.sql").exists(),
        "invalid placeholder migration filename must not remain",
    )
    migration_src = _read(MIGRATION)
    _contains_all(
        migration_src,
        [
            "add column if not exists deleted_at timestamptz null",
            "where deleted_at is null",
            "soft archive",
        ],
        label="migration",
    )
    print("  [OK] migration has deleted_at + active partial index + soft archive comment")

    files_route_src = _read(FILES_ROUTE)
    _contains_all(
        files_route_src,
        [
            "deleted_at: str | None = None",
            'deleted_at=row.get("deleted_at")',
            "include_deleted: bool = Query(default=False)",
            "created_at,deleted_at",
            'params["deleted_at"] = "is.null"',
            "_is_missing_deleted_at_column_error",
            "legacy_params",
            "file archive metadata migration is not applied",
            "supabase.update_rows(",
            'payload={"deleted_at": archived_at}',
            'operation="archive file metadata"',
        ],
        label="api-files-route",
    )
    _contains_none(
        files_route_src,
        [
            'supabase.delete_rows(\n            table="app.file_objects"',
            "operation=\"delete file metadata\"",
        ],
        label="api-hard-delete",
    )
    print("  [OK] api/routes/files.py uses include_deleted + active filter + soft archive update")

    project_detail_src = _read(PROJECT_DETAIL_PAGE)
    _contains_all(
        project_detail_src,
        [
            "include_preflight_summary: true",
            "include_part_creation_projection: true",
            "projectDetailIntakeStatus(file)",
            "Project-ready files",
            "Intake attention",
            "Manage in DXF Intake",
            "Hide upload",
            "Archive upload",
        ],
        label="project-detail",
    )
    _contains_none(
        project_detail_src,
        ['file.validation_status ?? "pending"'],
        label="legacy-pending-fallback",
    )
    print("  [OK] ProjectDetailPage uses intake-aware flags/statuses and no legacy pending fallback")

    mock_api_src = _read(MOCK_API)
    _contains_all(
        mock_api_src,
        [
            "include_deleted",
            "!item.deleted_at",
            "if (fileItemMatch && method === \"DELETE\")",
            "deleted_at",
        ],
        label="mock-api",
    )
    print("  [OK] mock API supports DELETE archive behavior and active-list filtering")

    _assert(E2E_SPEC.is_file(), f"missing e2e spec: {E2E_SPEC}")
    print("  [OK] E2E spec file exists")

    _assert(CANVAS.is_file(), f"missing task canvas: {CANVAS}")
    _assert(YAML.is_file(), f"missing task yaml: {YAML}")
    _assert(RUN_PROMPT.is_file(), f"missing task run prompt: {RUN_PROMPT}")
    _assert(not DUPLICATE_CANVAS.exists(), f"unexpected root-level duplicate canvas: {DUPLICATE_CANVAS}")
    _assert(not DUPLICATE_YAML.exists(), f"unexpected root-level duplicate yaml: {DUPLICATE_YAML}")
    print("  [OK] task artifacts are in web_platform paths with no root-level duplicate canvas/yaml")

    print("All checks passed.")


if __name__ == "__main__":
    main()
