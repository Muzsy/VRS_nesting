#!/usr/bin/env python3
"""DXF Prefilter E4-T3 smoke checks.

Deterministic smoke that validates:
- file-list latest preflight projection now includes T3 fields,
- DxfIntakePage renders the latest runs table columns and helper tokens,
- frontend type/API boundary contains the new summary fields.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser
from api.routes.files import list_project_files


class FakeSupabase:
    def __init__(
        self,
        *,
        files_rows: list[dict[str, Any]],
        preflight_rows: list[dict[str, Any]],
    ) -> None:
        self._files_rows = files_rows
        self._preflight_rows = preflight_rows

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        if table == "app.projects":
            return [{"id": "project-row"}]
        if table == "app.file_objects":
            return list(self._files_rows)
        if table == "app.preflight_runs":
            raw_filter = str(params.get("source_file_object_id", ""))
            source_ids = set()
            if raw_filter.startswith("in.(") and raw_filter.endswith(")"):
                source_ids = set(token for token in raw_filter[4:-1].split(",") if token)
            rows = [row for row in self._preflight_rows if str(row.get("source_file_object_id", "")) in source_ids]
            return sorted(
                rows,
                key=lambda row: (
                    str(row.get("source_file_object_id", "")),
                    -(int(row.get("run_seq")) if isinstance(row.get("run_seq"), int) else -1),
                ),
            )
        raise AssertionError(f"unexpected table query: {table}")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        print(f"  FAIL: {message}")
        raise SystemExit(1)


def _scenario(name: str) -> None:
    print(f"  {name} ... ", end="", flush=True)


def _ok() -> None:
    print("OK")


def scenario_route_projection_contains_t3_fields() -> None:
    _scenario("ROUTE PROJECTION T3 FIELDS")
    project_id = str(uuid4())
    file_id = str(uuid4())

    files_rows = [
        {
            "id": file_id,
            "project_id": project_id,
            "storage_bucket": "source-files",
            "storage_path": f"projects/{project_id}/files/{file_id}/part.dxf",
            "file_name": "part.dxf",
            "mime_type": "application/dxf",
            "file_kind": "source_dxf",
            "byte_size": 128,
            "sha256": "hash",
            "uploaded_by": "user-1",
            "created_at": "2026-04-21T00:00:00+00:00",
        }
    ]
    preflight_rows = [
        {
            "id": "run-1",
            "source_file_object_id": file_id,
            "run_seq": 1,
            "run_status": "preflight_complete",
            "acceptance_outcome": "preflight_review_required",
            "finished_at": "2026-04-21T10:00:00+00:00",
            "summary_jsonb": {
                "issue_summary": {
                    "counts_by_severity": {
                        "blocking": 0,
                        "review_required": 2,
                        "warning": 1,
                        "info": 0,
                    }
                },
                "repair_summary": {
                    "counts": {
                        "applied_gap_repair_count": 1,
                        "applied_duplicate_dedupe_count": 1,
                    }
                },
            },
        }
    ]

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        user=AuthenticatedUser(id="user-1", access_token="token"),
        supabase=FakeSupabase(files_rows=files_rows, preflight_rows=preflight_rows),
    )

    summary = response.items[0].latest_preflight_summary
    _assert(summary is not None, "latest_preflight_summary should be present")
    _assert(summary.get("blocking_issue_count") == 0, "blocking_issue_count mismatch")
    _assert(summary.get("review_required_issue_count") == 2, "review_required_issue_count mismatch")
    _assert(summary.get("warning_issue_count") == 1, "warning_issue_count mismatch")
    _assert(summary.get("total_issue_count") == 3, "total_issue_count mismatch")
    _assert(summary.get("applied_gap_repair_count") == 1, "applied_gap_repair_count mismatch")
    _assert(summary.get("applied_duplicate_dedupe_count") == 1, "applied_duplicate_dedupe_count mismatch")
    _assert(summary.get("total_repair_count") == 2, "total_repair_count mismatch")
    _assert(
        summary.get("recommended_action") == "review_required_wait_for_diagnostics",
        "recommended_action mismatch",
    )
    _ok()


def scenario_intake_table_and_helpers_present() -> None:
    _scenario("INTAKE TABLE + BADGE HELPERS")
    src = (ROOT / "frontend/src/pages/DxfIntakePage.tsx").read_text(encoding="utf-8")

    required_tokens = [
        "Latest preflight runs",
        "Run status",
        "Issues",
        "Repairs",
        "Acceptance",
        "Recommended action",
        "Finished",
        "formatRunStatusBadge(",
        "formatAcceptanceOutcomeBadge(",
        "formatIssueCountBadge(",
        "formatRepairCountBadge(",
        "formatRecommendedActionLabel(",
    ]
    for token in required_tokens:
        _assert(token in src, f"missing intake table/helper token: {token}")
    _ok()


def scenario_frontend_boundary_contains_new_summary_fields() -> None:
    _scenario("FRONTEND TYPES/API SUMMARY FIELDS")
    types_src = (ROOT / "frontend/src/lib/types.ts").read_text(encoding="utf-8")
    api_src = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")
    route_src = (ROOT / "api/routes/files.py").read_text(encoding="utf-8")

    required_field_tokens = [
        "blocking_issue_count",
        "review_required_issue_count",
        "warning_issue_count",
        "total_issue_count",
        "applied_gap_repair_count",
        "applied_duplicate_dedupe_count",
        "total_repair_count",
        "recommended_action",
    ]
    for token in required_field_tokens:
        _assert(token in types_src, f"missing types token: {token}")
        _assert(token in api_src, f"missing api token: {token}")
        _assert(token in route_src, f"missing route token: {token}")

    _assert("summary_jsonb" in route_src, "route should query summary_jsonb")
    _ok()


def main() -> None:
    print("DXF Prefilter E4-T3 smoke:")
    scenario_route_projection_contains_t3_fields()
    scenario_intake_table_and_helpers_present()
    scenario_frontend_boundary_contains_new_summary_fields()
    print("All smoke scenarios passed.")


if __name__ == "__main__":
    main()
