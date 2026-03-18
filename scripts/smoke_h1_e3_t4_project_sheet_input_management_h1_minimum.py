#!/usr/bin/env python3
"""H1-E3-T4 smoke: project sheet input management (H1 minimum)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser, get_current_user
from api.deps import get_supabase_client
from api.routes.project_sheet_inputs import router as project_sheet_inputs_router
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.sheet_definitions: dict[str, dict[str, Any]] = {}
        self.sheet_revisions: dict[str, dict[str, Any]] = {}
        self.project_sheet_inputs: dict[str, dict[str, Any]] = {}

    def _rows_for_table(self, table: str) -> list[dict[str, Any]]:
        if table == "app.projects":
            return list(self.projects.values())
        if table == "app.sheet_definitions":
            return list(self.sheet_definitions.values())
        if table == "app.sheet_revisions":
            return list(self.sheet_revisions.values())
        if table == "app.project_sheet_inputs":
            return list(self.project_sheet_inputs.values())
        return []

    @staticmethod
    def _matches(row: dict[str, Any], key: str, raw_filter: str) -> bool:
        value = row.get(key)
        if raw_filter.startswith("eq."):
            return str(value) == raw_filter[3:]
        if raw_filter.startswith("neq."):
            return str(value) != raw_filter[4:]
        return True

    @staticmethod
    def _apply_order(rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
        ordered = list(rows)
        for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
            key = token.split(".")[0]
            reverse = ".desc" in token
            ordered.sort(key=lambda row: str(row.get(key) or ""), reverse=reverse)
        return ordered

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = self._rows_for_table(table)
        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        order_clause = params.get("order", "").strip()
        if order_clause:
            rows = self._apply_order(rows, order_clause)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = params.get("limit", "")
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]
        return [dict(row) for row in rows]

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        now = datetime.now(timezone.utc).isoformat()
        row = dict(payload)

        if table == "app.project_sheet_inputs":
            for existing in self.project_sheet_inputs.values():
                if (
                    str(existing.get("project_id")) == str(row.get("project_id"))
                    and str(existing.get("sheet_revision_id")) == str(row.get("sheet_revision_id"))
                ):
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint project_sheet_inputs_project_id_sheet_revision_id_key"
                    )
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.project_sheet_inputs[str(row["id"])] = row
            return dict(row)

        raise RuntimeError(f"unsupported table insert: {table}")

    def update_rows(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        if table != "app.project_sheet_inputs":
            return []

        rows = list(self.project_sheet_inputs.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            current = self.project_sheet_inputs[str(row["id"])]
            current.update(payload)
            current["updated_at"] = now
            updated.append(dict(current))
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = (table, access_token, filters)


def _build_test_app(fake: FakeSupabaseClient) -> FastAPI:
    app = FastAPI()
    app.include_router(project_sheet_inputs_router, prefix="/v1")
    app.dependency_overrides[get_supabase_client] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000001",
        email="u1@example.com",
        access_token="token-u1",
    )
    return app


def _seed_project(fake: FakeSupabaseClient, *, project_id: str, owner_user_id: str) -> None:
    fake.projects[project_id] = {
        "id": project_id,
        "owner_user_id": owner_user_id,
        "lifecycle": "draft",
    }


def _seed_sheet_revision(
    fake: FakeSupabaseClient,
    *,
    owner_user_id: str,
    code: str,
    name: str,
    revision_no: int,
) -> str:
    sheet_definition_id = str(uuid4())
    sheet_revision_id = str(uuid4())
    fake.sheet_definitions[sheet_definition_id] = {
        "id": sheet_definition_id,
        "owner_user_id": owner_user_id,
        "code": code,
        "name": name,
        "current_revision_id": sheet_revision_id,
    }
    fake.sheet_revisions[sheet_revision_id] = {
        "id": sheet_revision_id,
        "sheet_definition_id": sheet_definition_id,
        "revision_no": revision_no,
        "lifecycle": "draft",
        "width_mm": 1000.0,
        "height_mm": 1000.0,
    }
    return sheet_revision_id


def main() -> int:
    fake = FakeSupabaseClient()
    test_app = _build_test_app(fake)
    try:
        client = TestClient(test_app)
        owner_id = "00000000-0000-0000-0000-000000000001"
        other_owner_id = "00000000-0000-0000-0000-000000000002"

        project_id = str(uuid4())
        foreign_project_id = str(uuid4())
        _seed_project(fake, project_id=project_id, owner_user_id=owner_id)
        _seed_project(fake, project_id=foreign_project_id, owner_user_id=other_owner_id)

        own_revision_a = _seed_sheet_revision(
            fake,
            owner_user_id=owner_id,
            code="SHEET-A",
            name="Sheet A",
            revision_no=1,
        )
        own_revision_b = _seed_sheet_revision(
            fake,
            owner_user_id=owner_id,
            code="SHEET-B",
            name="Sheet B",
            revision_no=1,
        )
        foreign_revision = _seed_sheet_revision(
            fake,
            owner_user_id=other_owner_id,
            code="SHEET-X",
            name="Sheet X",
            revision_no=1,
        )

        create_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            json={
                "sheet_revision_id": own_revision_a,
                "required_qty": 4,
                "is_active": True,
                "is_default": True,
                "placement_priority": 40,
                "notes": "first row",
            },
        )
        if create_resp.status_code != 201:
            raise RuntimeError(f"create branch failed: {create_resp.status_code} {create_resp.text}")
        created = create_resp.json()
        if created.get("was_existing_input"):
            raise RuntimeError("create branch should return was_existing_input=false")
        first_id = str(created.get("project_sheet_input_id") or "")
        if not first_id:
            raise RuntimeError("create branch returned empty id")
        if len(fake.project_sheet_inputs) != 1:
            raise RuntimeError("create branch should insert one project_sheet_input row")

        update_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            json={
                "sheet_revision_id": own_revision_a,
                "required_qty": 9,
                "is_active": False,
                "is_default": False,
                "placement_priority": 35,
                "notes": "updated row",
            },
        )
        if update_resp.status_code != 201:
            raise RuntimeError(f"update branch failed: {update_resp.status_code} {update_resp.text}")
        updated = update_resp.json()
        if not updated.get("was_existing_input"):
            raise RuntimeError("update branch should return was_existing_input=true")
        if str(updated.get("project_sheet_input_id") or "") != first_id:
            raise RuntimeError("update branch should reuse existing row id")
        if len(fake.project_sheet_inputs) != 1:
            raise RuntimeError("update branch should not create duplicate row")
        current_first = fake.project_sheet_inputs[first_id]
        if int(current_first.get("required_qty") or 0) != 9:
            raise RuntimeError("update branch did not update required_qty")
        if bool(current_first.get("is_active")):
            raise RuntimeError("update branch did not update is_active")

        second_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            json={
                "sheet_revision_id": own_revision_b,
                "required_qty": 2,
                "is_active": True,
                "is_default": True,
                "placement_priority": 10,
                "notes": "second default row",
            },
        )
        if second_resp.status_code != 201:
            raise RuntimeError(f"second create failed: {second_resp.status_code} {second_resp.text}")
        second = second_resp.json()
        if second.get("was_existing_input"):
            raise RuntimeError("second create should be a new row")
        second_id = str(second.get("project_sheet_input_id") or "")
        if len(fake.project_sheet_inputs) != 2:
            raise RuntimeError("second create should increase row count to 2")

        first_after_default_switch = fake.project_sheet_inputs[first_id]
        second_after_default_switch = fake.project_sheet_inputs[second_id]
        if bool(first_after_default_switch.get("is_default")):
            raise RuntimeError("default-switch should clear previous default row")
        if not bool(second_after_default_switch.get("is_default")):
            raise RuntimeError("default-switch should keep the new row as default")

        list_resp = client.get(f"/v1/projects/{project_id}/sheet-inputs")
        if list_resp.status_code != 200:
            raise RuntimeError(f"list endpoint failed: {list_resp.status_code} {list_resp.text}")
        listed = list_resp.json()
        if int(listed.get("total") or 0) != 2:
            raise RuntimeError("list endpoint total mismatch")

        foreign_project_resp = client.post(
            f"/v1/projects/{foreign_project_id}/sheet-inputs",
            json={
                "sheet_revision_id": own_revision_a,
                "required_qty": 1,
            },
        )
        if foreign_project_resp.status_code != 404:
            raise RuntimeError(
                f"foreign project branch should fail with 404 (got {foreign_project_resp.status_code})"
            )

        foreign_revision_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            json={
                "sheet_revision_id": foreign_revision,
                "required_qty": 1,
            },
        )
        if foreign_revision_resp.status_code != 403:
            raise RuntimeError(
                f"foreign revision branch should fail with 403 (got {foreign_revision_resp.status_code})"
            )

        invalid_qty_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            json={
                "sheet_revision_id": own_revision_a,
                "required_qty": 0,
            },
        )
        if invalid_qty_resp.status_code != 422:
            raise RuntimeError(
                f"invalid qty branch should fail with 422 (got {invalid_qty_resp.status_code})"
            )

        invalid_priority_resp = client.post(
            f"/v1/projects/{project_id}/sheet-inputs",
            json={
                "sheet_revision_id": own_revision_a,
                "required_qty": 1,
                "placement_priority": 101,
            },
        )
        if invalid_priority_resp.status_code != 422:
            raise RuntimeError(
                f"invalid priority branch should fail with 422 (got {invalid_priority_resp.status_code})"
            )

        print("[PASS] H1-E3-T4 project sheet input management smoke passed")
        return 0
    finally:
        test_app.dependency_overrides.clear()


if __name__ == "__main__":
    raise SystemExit(main())
