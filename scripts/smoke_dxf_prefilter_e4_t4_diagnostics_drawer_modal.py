#!/usr/bin/env python3
"""DXF Prefilter E4-T4 smoke checks.

Deterministic smoke that validates:
- optional diagnostics projection on the existing file-list route,
- DxfIntakePage diagnostics trigger + drawer/modal section tokens,
- frontend type/API boundary for latest_preflight_diagnostics.
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
            source_ids: set[str] = set()
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


def scenario_route_projection_contains_latest_diagnostics() -> None:
    _scenario("ROUTE PROJECTION LATEST DIAGNOSTICS")
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
            "id": "run-2",
            "source_file_object_id": file_id,
            "run_seq": 2,
            "run_status": "preflight_complete",
            "acceptance_outcome": "preflight_review_required",
            "finished_at": "2026-04-21T10:00:00+00:00",
            "summary_jsonb": {
                "source_inventory_summary": {
                    "found_layers": ["CUT"],
                    "found_colors": [1],
                    "found_linetypes": ["CONTINUOUS"],
                    "entity_count": 10,
                    "contour_count": 3,
                    "open_path_layer_count": 1,
                    "open_path_total_count": 2,
                    "duplicate_candidate_group_count": 1,
                    "duplicate_candidate_member_count": 2,
                },
                "role_mapping_summary": {
                    "resolved_role_inventory": {"cut_contour": 3},
                    "layer_role_assignments": [{"layer": "CUT", "role": "cut_contour"}],
                    "review_required_count": 1,
                    "blocking_conflict_count": 0,
                },
                "issue_summary": {
                    "counts_by_severity": {
                        "blocking": 0,
                        "review_required": 1,
                        "warning": 0,
                        "info": 0,
                    },
                    "normalized_issues": [
                        {
                            "severity": "review_required",
                            "family": "layer_mapping_ambiguous",
                            "code": "DXF_LAYER_ROLE_AMBIGUOUS",
                            "message": "Layer ambiguity detected.",
                            "source": "role_resolver",
                        }
                    ],
                },
                "repair_summary": {
                    "counts": {
                        "applied_gap_repair_count": 1,
                        "applied_duplicate_dedupe_count": 0,
                        "skipped_source_entity_count": 0,
                        "remaining_open_path_count": 1,
                        "remaining_duplicate_count": 0,
                        "remaining_review_required_signal_count": 1,
                    },
                    "applied_gap_repairs": [],
                    "applied_duplicate_dedupes": [],
                    "skipped_source_entities": [],
                    "remaining_review_required_signals": [],
                },
                "acceptance_summary": {
                    "acceptance_outcome": "preflight_review_required",
                    "precedence_rule_applied": "blocking_then_review",
                    "importer_probe": {"is_pass": True},
                    "validator_probe": {"is_pass": False, "status": "warning"},
                    "blocking_reason_count": 0,
                    "review_required_reason_count": 1,
                },
                "artifact_references": [
                    {
                        "artifact_kind": "normalized_dxf",
                        "download_label": "Download normalized DXF",
                        "path": "/tmp/out/normalized.dxf",
                        "exists": False,
                    }
                ],
            },
        }
    ]

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        include_preflight_diagnostics=True,
        user=AuthenticatedUser(id="user-1", access_token="token"),
        supabase=FakeSupabase(files_rows=files_rows, preflight_rows=preflight_rows),
    )

    summary = response.items[0].latest_preflight_summary
    diagnostics = response.items[0].latest_preflight_diagnostics
    _assert(summary is not None, "latest_preflight_summary should be present")
    _assert(diagnostics is not None, "latest_preflight_diagnostics should be present")
    _assert(summary.get("preflight_run_id") == "run-2", "summary should use latest run")
    _assert(diagnostics["source_inventory_summary"]["found_layers"] == ["CUT"], "found_layers mismatch")
    _assert(
        diagnostics["issue_summary"]["normalized_issues"][0]["family"] == "layer_mapping_ambiguous",
        "normalized issues mismatch",
    )
    _assert(diagnostics["artifact_references"][0]["download_label"] == "Download normalized DXF", "artifact label mismatch")
    _ok()


def scenario_intake_drawer_tokens_present() -> None:
    _scenario("INTAKE VIEW DIAGNOSTICS + DRAWER TOKENS")
    src = (ROOT / "frontend/src/pages/DxfIntakePage.tsx").read_text(encoding="utf-8")

    required_tokens = [
        "View diagnostics",
        "selectedDiagnosticsFileId",
        "Diagnostics",
        "Source inventory",
        "Role mapping",
        "Issues",
        "Repairs",
        "Acceptance",
        "Artifacts",
        "latest_preflight_diagnostics",
        "include_preflight_diagnostics: true",
    ]
    for token in required_tokens:
        _assert(token in src, f"missing intake diagnostics token: {token}")
    _ok()


def scenario_frontend_and_route_boundary_tokens_present() -> None:
    _scenario("FRONTEND/ROUTE DIAGNOSTICS BOUNDARY")
    types_src = (ROOT / "frontend/src/lib/types.ts").read_text(encoding="utf-8")
    api_src = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")
    route_src = (ROOT / "api/routes/files.py").read_text(encoding="utf-8")

    required_tokens = [
        "ProjectFileLatestPreflightDiagnostics",
        "latest_preflight_diagnostics",
        "include_preflight_diagnostics",
        "source_inventory_summary",
        "role_mapping_summary",
        "issue_summary",
        "repair_summary",
        "acceptance_summary",
        "artifact_references",
    ]
    for token in required_tokens:
        _assert(token in types_src or token in api_src or token in route_src, f"missing token: {token}")

    _assert("include_preflight_diagnostics" in route_src, "route optional diagnostics query missing")
    _assert("latest_preflight_diagnostics" in route_src, "route diagnostics projection missing")
    _ok()


def main() -> None:
    print("DXF Prefilter E4-T4 smoke:")
    scenario_route_projection_contains_latest_diagnostics()
    scenario_intake_drawer_tokens_present()
    scenario_frontend_and_route_boundary_tokens_present()
    print("All smoke scenarios passed.")


if __name__ == "__main__":
    main()
