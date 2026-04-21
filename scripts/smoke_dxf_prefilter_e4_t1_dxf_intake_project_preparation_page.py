#!/usr/bin/env python3
"""DXF Prefilter E4-T1 smoke checks.

Deterministic smoke that validates:
- optional file-list preflight summary projection contract,
- new intake route presence,
- ProjectDetail -> intake CTA presence.
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


def scenario_file_list_projection_contract() -> None:
    _scenario("FILE-LIST SUMMARY PROJECTION")
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
            "acceptance_outcome": "accepted_for_import",
            "finished_at": "2026-04-21T10:00:00+00:00",
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
    _assert(summary.get("preflight_run_id") == "run-1", "preflight_run_id mismatch")
    _assert(summary.get("run_seq") == 1, "run_seq mismatch")
    _assert(summary.get("run_status") == "preflight_complete", "run_status mismatch")
    _assert(summary.get("acceptance_outcome") == "accepted_for_import", "acceptance_outcome mismatch")
    _assert(summary.get("finished_at") == "2026-04-21T10:00:00+00:00", "finished_at mismatch")
    _ok()


def scenario_intake_route_present() -> None:
    _scenario("INTAKE ROUTE PRESENT")
    app_src = (ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")
    _assert('/projects/:projectId/dxf-intake' in app_src, "missing /projects/:projectId/dxf-intake route")
    _assert("DxfIntakePage" in app_src, "DxfIntakePage import/usage missing")
    _ok()


def scenario_project_detail_cta_present() -> None:
    _scenario("PROJECT DETAIL CTA")
    detail_src = (ROOT / "frontend/src/pages/ProjectDetailPage.tsx").read_text(encoding="utf-8")
    _assert("/dxf-intake" in detail_src, "missing project detail -> intake navigation")
    _assert("DXF intake / preparation" in detail_src, "missing explicit intake CTA label")
    _ok()


def main() -> None:
    print("DXF Prefilter E4-T1 smoke:")
    scenario_file_list_projection_contract()
    scenario_intake_route_present()
    scenario_project_detail_cta_present()
    print("All smoke scenarios passed.")


if __name__ == "__main__":
    main()
