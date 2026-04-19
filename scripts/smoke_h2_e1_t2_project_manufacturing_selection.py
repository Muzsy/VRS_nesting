#!/usr/bin/env python3
"""H2-E1-T2 smoke: project manufacturing selection."""

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
from api.routes.project_manufacturing_selection import router as project_manufacturing_selection_router
from api.supabase_client import SupabaseHTTPError


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}
        self.manufacturing_profiles: dict[str, dict[str, Any]] = {}
        self.manufacturing_profile_versions: dict[str, dict[str, Any]] = {}
        self.project_technology_setups: dict[str, dict[str, Any]] = {}
        self.project_manufacturing_selection: dict[str, dict[str, Any]] = {}

    def _rows_for_table(self, table: str) -> list[dict[str, Any]]:
        if table == "app.projects":
            return list(self.projects.values())
        if table == "app.manufacturing_profiles":
            return list(self.manufacturing_profiles.values())
        if table == "app.manufacturing_profile_versions":
            return list(self.manufacturing_profile_versions.values())
        if table == "app.project_technology_setups":
            return list(self.project_technology_setups.values())
        if table == "app.project_manufacturing_selection":
            return list(self.project_manufacturing_selection.values())
        return []

    @staticmethod
    def _normalize_bool(raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            cleaned = raw.strip().lower()
            if cleaned in {"true", "t", "1", "yes", "y"}:
                return True
            if cleaned in {"false", "f", "0", "no", "n"}:
                return False
        if isinstance(raw, (int, float)):
            return bool(raw)
        return bool(raw)

    @classmethod
    def _matches(cls, row: dict[str, Any], key: str, raw_filter: str) -> bool:
        value = row.get(key)
        if raw_filter.startswith("eq."):
            expected = raw_filter[3:]
            if expected in {"true", "false"}:
                return cls._normalize_bool(value) is (expected == "true")
            return str(value) == expected
        if raw_filter.startswith("neq."):
            expected = raw_filter[4:]
            if expected in {"true", "false"}:
                return cls._normalize_bool(value) is not (expected == "true")
            return str(value) != expected
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
        if table != "app.project_manufacturing_selection":
            raise RuntimeError(f"unsupported table insert: {table}")

        row = dict(payload)
        project_id = str(row.get("project_id") or "").strip()
        if not project_id:
            raise RuntimeError("project_manufacturing_selection insert with empty project_id")
        if project_id in self.project_manufacturing_selection:
            raise SupabaseHTTPError(
                "duplicate key value violates unique constraint project_manufacturing_selection_pkey"
            )

        row.setdefault("selected_at", datetime.now(timezone.utc).isoformat())
        self.project_manufacturing_selection[project_id] = row
        return dict(row)

    def update_rows(
        self,
        *,
        table: str,
        access_token: str,
        payload: dict[str, Any],
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        if table != "app.project_manufacturing_selection":
            return []

        rows = list(self.project_manufacturing_selection.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        for row in rows:
            project_id = str(row.get("project_id") or "").strip()
            current = self.project_manufacturing_selection[project_id]
            current.update(payload)
            updated.append(dict(current))
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        if table != "app.project_manufacturing_selection":
            return

        delete_keys: list[str] = []
        for project_id, row in self.project_manufacturing_selection.items():
            keep = True
            for key, raw_filter in filters.items():
                if not self._matches(row, key, raw_filter):
                    keep = False
                    break
            if keep:
                delete_keys.append(project_id)

        for key in delete_keys:
            self.project_manufacturing_selection.pop(key, None)


def _build_test_app(fake: FakeSupabaseClient) -> FastAPI:
    app = FastAPI()
    app.include_router(project_manufacturing_selection_router, prefix="/v1")
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


def _seed_manufacturing_profile(
    fake: FakeSupabaseClient,
    *,
    profile_id: str,
    owner_user_id: str,
    profile_name: str,
) -> None:
    fake.manufacturing_profiles[profile_id] = {
        "id": profile_id,
        "owner_user_id": owner_user_id,
        "profile_name": profile_name,
    }


def _seed_manufacturing_version(
    fake: FakeSupabaseClient,
    *,
    version_id: str,
    manufacturing_profile_id: str,
    owner_user_id: str,
    version_no: int,
    thickness_mm: float,
    is_active: bool,
) -> None:
    fake.manufacturing_profile_versions[version_id] = {
        "id": version_id,
        "manufacturing_profile_id": manufacturing_profile_id,
        "owner_user_id": owner_user_id,
        "version_no": version_no,
        "is_active": is_active,
        "lifecycle": "approved",
        "thickness_mm": thickness_mm,
        "kerf_mm": 0.2,
    }


def _seed_project_technology_setup(
    fake: FakeSupabaseClient,
    *,
    setup_id: str,
    project_id: str,
    thickness_mm: float,
    is_default: bool,
) -> None:
    fake.project_technology_setups[setup_id] = {
        "id": setup_id,
        "project_id": project_id,
        "lifecycle": "approved",
        "is_default": is_default,
        "thickness_mm": thickness_mm,
        "machine_code": "LASER-A",
        "material_code": "S235",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


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

        own_profile_id = str(uuid4())
        foreign_profile_id = str(uuid4())
        _seed_manufacturing_profile(
            fake,
            profile_id=own_profile_id,
            owner_user_id=owner_id,
            profile_name="Owner Profile",
        )
        _seed_manufacturing_profile(
            fake,
            profile_id=foreign_profile_id,
            owner_user_id=other_owner_id,
            profile_name="Foreign Profile",
        )

        own_version_a = str(uuid4())
        own_version_b = str(uuid4())
        own_inactive_version = str(uuid4())
        own_mismatch_version = str(uuid4())
        foreign_version = str(uuid4())

        _seed_manufacturing_version(
            fake,
            version_id=own_version_a,
            manufacturing_profile_id=own_profile_id,
            owner_user_id=owner_id,
            version_no=1,
            thickness_mm=10.0,
            is_active=True,
        )
        _seed_manufacturing_version(
            fake,
            version_id=own_version_b,
            manufacturing_profile_id=own_profile_id,
            owner_user_id=owner_id,
            version_no=2,
            thickness_mm=10.0,
            is_active=True,
        )
        _seed_manufacturing_version(
            fake,
            version_id=own_inactive_version,
            manufacturing_profile_id=own_profile_id,
            owner_user_id=owner_id,
            version_no=3,
            thickness_mm=10.0,
            is_active=False,
        )
        _seed_manufacturing_version(
            fake,
            version_id=own_mismatch_version,
            manufacturing_profile_id=own_profile_id,
            owner_user_id=owner_id,
            version_no=4,
            thickness_mm=12.0,
            is_active=True,
        )
        _seed_manufacturing_version(
            fake,
            version_id=foreign_version,
            manufacturing_profile_id=foreign_profile_id,
            owner_user_id=other_owner_id,
            version_no=1,
            thickness_mm=10.0,
            is_active=True,
        )

        _seed_project_technology_setup(
            fake,
            setup_id=str(uuid4()),
            project_id=project_id,
            thickness_mm=10.0,
            is_default=True,
        )

        create_resp = client.put(
            f"/v1/projects/{project_id}/manufacturing-selection",
            json={"active_manufacturing_profile_version_id": own_version_a},
        )
        if create_resp.status_code != 200:
            raise RuntimeError(f"create branch failed: {create_resp.status_code} {create_resp.text}")
        create_payload = create_resp.json()
        if create_payload.get("was_existing_selection"):
            raise RuntimeError("create branch should return was_existing_selection=false")
        if str(create_payload.get("active_manufacturing_profile_version_id") or "") != own_version_a:
            raise RuntimeError("create branch returned unexpected version id")

        overwrite_resp = client.put(
            f"/v1/projects/{project_id}/manufacturing-selection",
            json={"active_manufacturing_profile_version_id": own_version_b},
        )
        if overwrite_resp.status_code != 200:
            raise RuntimeError(f"overwrite branch failed: {overwrite_resp.status_code} {overwrite_resp.text}")
        overwrite_payload = overwrite_resp.json()
        if not overwrite_payload.get("was_existing_selection"):
            raise RuntimeError("overwrite branch should return was_existing_selection=true")
        if str(overwrite_payload.get("active_manufacturing_profile_version_id") or "") != own_version_b:
            raise RuntimeError("overwrite branch returned unexpected version id")
        if len(fake.project_manufacturing_selection) != 1:
            raise RuntimeError("overwrite branch should keep exactly one selection row")

        get_resp = client.get(f"/v1/projects/{project_id}/manufacturing-selection")
        if get_resp.status_code != 200:
            raise RuntimeError(f"get branch failed: {get_resp.status_code} {get_resp.text}")
        get_payload = get_resp.json()
        if str(get_payload.get("active_manufacturing_profile_version_id") or "") != own_version_b:
            raise RuntimeError("get branch returned unexpected selected version")

        delete_resp = client.delete(f"/v1/projects/{project_id}/manufacturing-selection")
        if delete_resp.status_code != 204:
            raise RuntimeError(f"delete branch failed: {delete_resp.status_code} {delete_resp.text}")
        if fake.project_manufacturing_selection:
            raise RuntimeError("delete branch should remove the selection row")

        get_after_delete_resp = client.get(f"/v1/projects/{project_id}/manufacturing-selection")
        if get_after_delete_resp.status_code != 404:
            raise RuntimeError(
                f"get-after-delete branch should fail with 404 (got {get_after_delete_resp.status_code})"
            )

        foreign_project_resp = client.put(
            f"/v1/projects/{foreign_project_id}/manufacturing-selection",
            json={"active_manufacturing_profile_version_id": own_version_a},
        )
        if foreign_project_resp.status_code != 404:
            raise RuntimeError(
                f"foreign project branch should fail with 404 (got {foreign_project_resp.status_code})"
            )

        foreign_version_resp = client.put(
            f"/v1/projects/{project_id}/manufacturing-selection",
            json={"active_manufacturing_profile_version_id": foreign_version},
        )
        if foreign_version_resp.status_code != 403:
            raise RuntimeError(
                f"foreign version branch should fail with 403 (got {foreign_version_resp.status_code})"
            )

        inactive_version_resp = client.put(
            f"/v1/projects/{project_id}/manufacturing-selection",
            json={"active_manufacturing_profile_version_id": own_inactive_version},
        )
        if inactive_version_resp.status_code != 400:
            raise RuntimeError(
                f"inactive version branch should fail with 400 (got {inactive_version_resp.status_code})"
            )

        mismatch_resp = client.put(
            f"/v1/projects/{project_id}/manufacturing-selection",
            json={"active_manufacturing_profile_version_id": own_mismatch_version},
        )
        if mismatch_resp.status_code != 400:
            raise RuntimeError(
                f"thickness mismatch branch should fail with 400 (got {mismatch_resp.status_code})"
            )

    except Exception as exc:
        print(f"[FAIL] smoke_h2_e1_t2_project_manufacturing_selection: {exc}", file=sys.stderr)
        return 1

    print("[PASS] smoke_h2_e1_t2_project_manufacturing_selection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
