from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

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
        self.calls: list[tuple[str, dict[str, str]]] = []

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        self.calls.append((table, dict(params)))
        if table == "app.projects":
            return [{"id": "project-row"}]
        if table == "app.file_objects":
            return list(self._files_rows)
        if table == "app.preflight_runs":
            raw_filter = str(params.get("source_file_object_id", ""))
            source_ids: set[str] = set()
            if raw_filter.startswith("in.(") and raw_filter.endswith(")"):
                source_ids = set(token for token in raw_filter[4:-1].split(",") if token)
            rows = [
                row
                for row in self._preflight_rows
                if str(row.get("source_file_object_id", "")) in source_ids
            ]
            return sorted(
                rows,
                key=lambda row: (
                    str(row.get("source_file_object_id", "")),
                    -(int(row.get("run_seq")) if isinstance(row.get("run_seq"), int) else -1),
                ),
            )
        raise AssertionError(f"unexpected table query: {table}")


def _file_row(file_id: str, *, project_id: str) -> dict[str, Any]:
    return {
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


def _auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(id="user-1", access_token="token")


def test_list_project_files_without_summary_and_diagnostics_does_not_query_preflight_runs() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(files_rows=[_file_row(file_id, project_id=project_id)], preflight_rows=[])

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=False,
        include_preflight_diagnostics=False,
        user=_auth_user(),
        supabase=supabase,
    )

    assert response.total == 1
    assert response.items[0].latest_preflight_summary is None
    assert response.items[0].latest_preflight_diagnostics is None
    assert not any(table == "app.preflight_runs" for table, _ in supabase.calls)


def test_list_project_files_with_diagnostics_true_projects_latest_diagnostics_shape() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(
        files_rows=[_file_row(file_id, project_id=project_id)],
        preflight_rows=[
            {
                "id": "run-1",
                "source_file_object_id": file_id,
                "run_seq": 1,
                "run_status": "preflight_complete",
                "acceptance_outcome": "preflight_review_required",
                "finished_at": "2026-04-21T10:00:00+00:00",
                "summary_jsonb": {
                    "source_inventory_summary": {
                        "found_layers": ["CUT", "MARK"],
                        "found_colors": [1, 2, -7],
                        "found_linetypes": ["CONTINUOUS"],
                        "entity_count": 13,
                        "contour_count": 4,
                        "open_path_layer_count": 1,
                        "open_path_total_count": 2,
                        "duplicate_candidate_group_count": 1,
                        "duplicate_candidate_member_count": 2,
                    },
                    "role_mapping_summary": {
                        "resolved_role_inventory": {"cut_contour": 4},
                        "layer_role_assignments": [{"layer": "CUT", "role": "cut_contour"}],
                        "review_required_count": 1,
                        "blocking_conflict_count": 0,
                    },
                    "issue_summary": {
                        "counts_by_severity": {
                            "blocking": 0,
                            "review_required": 1,
                            "warning": 2,
                            "info": 3,
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
                            "applied_duplicate_dedupe_count": 2,
                            "skipped_source_entity_count": 0,
                            "remaining_open_path_count": 3,
                            "remaining_duplicate_count": 1,
                            "remaining_review_required_signal_count": 1,
                        },
                        "applied_gap_repairs": [{"id": "gap-1"}],
                        "applied_duplicate_dedupes": [{"id": "dup-1"}],
                        "skipped_source_entities": [],
                        "remaining_review_required_signals": [{"family": "writer_skipped_source_entity"}],
                    },
                    "acceptance_summary": {
                        "acceptance_outcome": "preflight_review_required",
                        "precedence_rule_applied": "blocking_then_review",
                        "importer_probe": {"is_pass": True, "error_code": None},
                        "validator_probe": {"is_pass": False, "status": "warning"},
                        "blocking_reason_count": 0,
                        "review_required_reason_count": 1,
                    },
                    "artifact_references": [
                        {
                            "artifact_kind": "normalized_dxf",
                            "download_label": "Download normalized DXF",
                            "path": "/tmp/out/normalized.dxf",
                            "exists": True,
                        }
                    ],
                },
            }
        ],
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=False,
        include_preflight_diagnostics=True,
        user=_auth_user(),
        supabase=supabase,
    )

    item = response.items[0]
    assert item.latest_preflight_summary is None
    diagnostics = item.latest_preflight_diagnostics
    assert diagnostics is not None
    assert diagnostics["source_inventory_summary"]["found_layers"] == ["CUT", "MARK"]
    assert diagnostics["source_inventory_summary"]["found_colors"] == [1, 2]
    assert diagnostics["role_mapping_summary"]["resolved_role_inventory"]["cut_contour"] == 4
    assert diagnostics["issue_summary"]["counts_by_severity"]["review_required"] == 1
    assert diagnostics["issue_summary"]["normalized_issues"][0]["code"] == "DXF_LAYER_ROLE_AMBIGUOUS"
    assert diagnostics["repair_summary"]["counts"]["applied_duplicate_dedupe_count"] == 2
    assert diagnostics["acceptance_summary"]["precedence_rule_applied"] == "blocking_then_review"
    assert diagnostics["artifact_references"][0]["download_label"] == "Download normalized DXF"


def test_list_project_files_with_diagnostics_true_is_null_safe_for_empty_summary_jsonb() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(
        files_rows=[_file_row(file_id, project_id=project_id)],
        preflight_rows=[
            {
                "id": "run-empty",
                "source_file_object_id": file_id,
                "run_seq": 1,
                "run_status": "preflight_complete",
                "acceptance_outcome": None,
                "finished_at": None,
                "summary_jsonb": {},
            }
        ],
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=False,
        include_preflight_diagnostics=True,
        user=_auth_user(),
        supabase=supabase,
    )

    diagnostics = response.items[0].latest_preflight_diagnostics
    assert diagnostics is not None
    assert diagnostics["source_inventory_summary"]["found_layers"] == []
    assert diagnostics["source_inventory_summary"]["entity_count"] == 0
    assert diagnostics["role_mapping_summary"]["resolved_role_inventory"] == {}
    assert diagnostics["issue_summary"]["normalized_issues"] == []
    assert diagnostics["repair_summary"]["counts"]["remaining_review_required_signal_count"] == 0
    assert diagnostics["acceptance_summary"]["acceptance_outcome"] == ""
    assert diagnostics["artifact_references"] == []


def test_list_project_files_with_summary_true_and_diagnostics_false_keeps_diagnostics_empty() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(
        files_rows=[_file_row(file_id, project_id=project_id)],
        preflight_rows=[
            {
                "id": "run-summary-only",
                "source_file_object_id": file_id,
                "run_seq": 2,
                "run_status": "preflight_complete",
                "acceptance_outcome": "accepted_for_import",
                "finished_at": "2026-04-21T10:05:00+00:00",
                "summary_jsonb": {"issue_summary": {"counts_by_severity": {"blocking": 0, "review_required": 0, "warning": 0, "info": 0}}},
            }
        ],
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        include_preflight_diagnostics=False,
        user=_auth_user(),
        supabase=supabase,
    )

    assert response.items[0].latest_preflight_summary is not None
    assert response.items[0].latest_preflight_diagnostics is None


def test_list_project_files_with_summary_and_diagnostics_uses_latest_run_per_file() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(
        files_rows=[_file_row(file_id, project_id=project_id)],
        preflight_rows=[
            {
                "id": "run-old",
                "source_file_object_id": file_id,
                "run_seq": 1,
                "run_status": "preflight_complete",
                "acceptance_outcome": "preflight_review_required",
                "finished_at": "2026-04-21T10:00:00+00:00",
                "summary_jsonb": {
                    "source_inventory_summary": {"found_layers": ["OLD"]},
                    "issue_summary": {"counts_by_severity": {"blocking": 1, "review_required": 0, "warning": 0, "info": 0}},
                },
            },
            {
                "id": "run-new",
                "source_file_object_id": file_id,
                "run_seq": 2,
                "run_status": "preflight_complete",
                "acceptance_outcome": "accepted_for_import",
                "finished_at": "2026-04-21T10:10:00+00:00",
                "summary_jsonb": {
                    "source_inventory_summary": {"found_layers": ["NEW"]},
                    "issue_summary": {"counts_by_severity": {"blocking": 0, "review_required": 0, "warning": 1, "info": 0}},
                    "repair_summary": {"counts": {"applied_gap_repair_count": 1, "applied_duplicate_dedupe_count": 1}},
                },
            },
        ],
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        include_preflight_diagnostics=True,
        user=_auth_user(),
        supabase=supabase,
    )

    item = response.items[0]
    assert item.latest_preflight_summary is not None
    assert item.latest_preflight_summary["preflight_run_id"] == "run-new"
    assert item.latest_preflight_summary["run_seq"] == 2
    assert item.latest_preflight_summary["recommended_action"] == "ready_for_next_step"

    diagnostics = item.latest_preflight_diagnostics
    assert diagnostics is not None
    assert diagnostics["source_inventory_summary"]["found_layers"] == ["NEW"]
    assert diagnostics["issue_summary"]["counts_by_severity"]["blocking"] == 0
    assert diagnostics["repair_summary"]["counts"]["applied_gap_repair_count"] == 1
