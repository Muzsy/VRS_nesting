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


def test_list_project_files_without_preflight_summary_does_not_query_preflight_runs() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(files_rows=[_file_row(file_id, project_id=project_id)], preflight_rows=[])

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=False,
        user=_auth_user(),
        supabase=supabase,
    )

    assert response.total == 1
    assert response.items[0].latest_preflight_summary is None
    assert not any(table == "app.preflight_runs" for table, _ in supabase.calls)


def test_list_project_files_with_preflight_summary_allows_missing_summary() -> None:
    project_id = str(uuid4())
    file_a = str(uuid4())
    file_b = str(uuid4())
    supabase = FakeSupabase(
        files_rows=[
            _file_row(file_a, project_id=project_id),
            _file_row(file_b, project_id=project_id),
        ],
        preflight_rows=[],
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        user=_auth_user(),
        supabase=supabase,
    )

    assert response.total == 2
    assert [item.latest_preflight_summary for item in response.items] == [None, None]


def test_list_project_files_with_preflight_summary_picks_latest_run_per_file() -> None:
    project_id = str(uuid4())
    file_a = str(uuid4())
    file_b = str(uuid4())

    preflight_rows = [
        {
            "id": "run-a-1",
            "source_file_object_id": file_a,
            "run_seq": 1,
            "run_status": "preflight_complete",
            "acceptance_outcome": "preflight_rejected",
            "finished_at": "2026-04-21T12:00:00+00:00",
        },
        {
            "id": "run-a-2",
            "source_file_object_id": file_a,
            "run_seq": 2,
            "run_status": "preflight_complete",
            "acceptance_outcome": "accepted_for_import",
            "finished_at": "2026-04-21T12:10:00+00:00",
        },
        {
            "id": "run-b-1",
            "source_file_object_id": file_b,
            "run_seq": 1,
            "run_status": "preflight_complete",
            "acceptance_outcome": "preflight_review_required",
            "finished_at": "2026-04-21T12:20:00+00:00",
        },
    ]
    supabase = FakeSupabase(
        files_rows=[
            _file_row(file_a, project_id=project_id),
            _file_row(file_b, project_id=project_id),
        ],
        preflight_rows=preflight_rows,
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        user=_auth_user(),
        supabase=supabase,
    )

    by_file_id = {item.id: item for item in response.items}

    summary_a = by_file_id[file_a].latest_preflight_summary
    assert summary_a is not None
    assert summary_a["preflight_run_id"] == "run-a-2"
    assert summary_a["run_seq"] == 2
    assert summary_a["acceptance_outcome"] == "accepted_for_import"

    summary_b = by_file_id[file_b].latest_preflight_summary
    assert summary_b is not None
    assert summary_b["preflight_run_id"] == "run-b-1"
    assert summary_b["run_seq"] == 1
    assert summary_b["acceptance_outcome"] == "preflight_review_required"


def test_list_project_files_preflight_summary_remains_optional_when_fields_missing() -> None:
    project_id = str(uuid4())
    file_id = str(uuid4())
    supabase = FakeSupabase(
        files_rows=[_file_row(file_id, project_id=project_id)],
        preflight_rows=[
            {
                "id": "run-optional",
                "source_file_object_id": file_id,
                "run_seq": "n/a",
                "run_status": "preflight_complete",
                "acceptance_outcome": None,
                "finished_at": None,
            }
        ],
    )

    response = list_project_files(
        project_id=UUID(project_id),
        page=1,
        page_size=50,
        include_preflight_summary=True,
        user=_auth_user(),
        supabase=supabase,
    )

    summary = response.items[0].latest_preflight_summary
    assert summary is not None
    assert summary["preflight_run_id"] == "run-optional"
    assert summary["run_seq"] is None
    assert summary["acceptance_outcome"] is None
    assert summary["finished_at"] is None
