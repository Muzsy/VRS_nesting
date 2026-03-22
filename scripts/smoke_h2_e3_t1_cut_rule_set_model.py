#!/usr/bin/env python3
"""H2-E3-T1 smoke: cut rule set model — owner-scoped CRUD + versioning."""

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
from api.routes.cut_rule_sets import router as cut_rule_sets_router
from api.supabase_client import SupabaseHTTPError


# ---------------------------------------------------------------------------
# Fake Supabase client for cut_rule_sets
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.cut_rule_sets: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _matches(row: dict[str, Any], key: str, raw_filter: str) -> bool:
        value = row.get(key)
        if raw_filter.startswith("eq."):
            expected = raw_filter[3:]
            return str(value) == expected
        if raw_filter.startswith("neq."):
            expected = raw_filter[4:]
            return str(value) != expected
        return True

    @staticmethod
    def _apply_order(rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
        ordered = list(rows)
        for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
            key = token.split(".")[0]
            reverse = ".desc" in token
            ordered.sort(key=lambda row, k=key: str(row.get(k) or ""), reverse=reverse)
        return ordered

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        if table != "app.cut_rule_sets":
            return []

        rows = list(self.cut_rule_sets.values())
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
        if table != "app.cut_rule_sets":
            raise RuntimeError(f"unsupported table insert: {table}")

        row = dict(payload)
        row_id = str(row.get("id") or str(uuid4()))
        row["id"] = row_id

        # Check unique constraint: owner_user_id + name + version_no
        for existing in self.cut_rule_sets.values():
            if (
                existing.get("owner_user_id") == row.get("owner_user_id")
                and existing.get("name") == row.get("name")
                and existing.get("version_no") == row.get("version_no")
            ):
                raise SupabaseHTTPError(
                    "duplicate key value violates unique constraint cut_rule_sets_owner_user_id_name_version_no_key"
                )

        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        row.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        self.cut_rule_sets[row_id] = row
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
        if table != "app.cut_rule_sets":
            return []

        rows = list(self.cut_rule_sets.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        for row in rows:
            row_id = str(row.get("id") or "")
            current = self.cut_rule_sets[row_id]
            current.update(payload)
            updated.append(dict(current))
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        if table != "app.cut_rule_sets":
            return

        delete_keys: list[str] = []
        for row_id, row in self.cut_rule_sets.items():
            match = True
            for key, raw_filter in filters.items():
                if not self._matches(row, key, raw_filter):
                    match = False
                    break
            if match:
                delete_keys.append(row_id)

        for key in delete_keys:
            self.cut_rule_sets.pop(key, None)


# ---------------------------------------------------------------------------
# Test app builder
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_OWNER_ID = "00000000-0000-0000-0000-000000000002"


def _build_test_app(fake: FakeSupabaseClient, *, owner_id: str = OWNER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(cut_rule_sets_router, prefix="/v1")
    app.dependency_overrides[get_supabase_client] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=owner_id,
        email="u1@example.com",
        access_token="token-u1",
    )
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" — {detail}"
        print(msg, file=sys.stderr)


def main() -> int:
    global passed, failed
    fake = FakeSupabaseClient()
    app = _build_test_app(fake)
    client = TestClient(app)

    # -----------------------------------------------------------------------
    # Test 1: owner-scope create
    # -----------------------------------------------------------------------
    print("Test 1: owner-scope create")
    resp = client.post("/v1/cut-rule-sets", json={
        "name": "Steel Laser Defaults",
        "machine_code": "LASER-A",
        "material_code": "S235",
        "thickness_mm": 10.0,
    })
    _test("POST /cut-rule-sets -> 201", resp.status_code == 201, f"got {resp.status_code}")
    body = resp.json()
    created_id = body.get("id", "")
    _test("version_no == 1", body.get("version_no") == 1, f"got {body.get('version_no')}")
    _test("owner_user_id correct", body.get("owner_user_id") == OWNER_ID)
    _test("name correct", body.get("name") == "Steel Laser Defaults")

    # -----------------------------------------------------------------------
    # Test 2: same name -> new version
    # -----------------------------------------------------------------------
    print("Test 2: same name under same owner -> new version")
    resp2 = client.post("/v1/cut-rule-sets", json={
        "name": "Steel Laser Defaults",
        "machine_code": "LASER-A",
        "material_code": "S235",
        "thickness_mm": 12.0,
    })
    _test("POST same name -> 201", resp2.status_code == 201, f"got {resp2.status_code}")
    body2 = resp2.json()
    created_id_v2 = body2.get("id", "")
    _test("version_no == 2", body2.get("version_no") == 2, f"got {body2.get('version_no')}")

    # -----------------------------------------------------------------------
    # Test 3: list is owner-scoped
    # -----------------------------------------------------------------------
    print("Test 3: list is owner-scoped")
    # Seed a record for another owner directly in the fake store
    foreign_id = str(uuid4())
    fake.cut_rule_sets[foreign_id] = {
        "id": foreign_id,
        "owner_user_id": OTHER_OWNER_ID,
        "name": "Foreign Rules",
        "version_no": 1,
        "is_active": True,
        "machine_code": "OTHER",
        "material_code": "OTHER",
        "thickness_mm": 5.0,
        "metadata_jsonb": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    resp_list = client.get("/v1/cut-rule-sets")
    _test("GET /cut-rule-sets -> 200", resp_list.status_code == 200)
    items = resp_list.json()
    _test("list returns 2 own records (not 3)", len(items) == 2, f"got {len(items)}")
    all_owners = {item.get("owner_user_id") for item in items}
    _test("no foreign owner in list", all_owners == {OWNER_ID}, f"got {all_owners}")

    # -----------------------------------------------------------------------
    # Test 4: GET single record
    # -----------------------------------------------------------------------
    print("Test 4: GET single record")
    resp_get = client.get(f"/v1/cut-rule-sets/{created_id}")
    _test("GET /cut-rule-sets/{id} -> 200", resp_get.status_code == 200)
    _test("correct id returned", resp_get.json().get("id") == created_id)

    # foreign owner's record not accessible
    resp_foreign = client.get(f"/v1/cut-rule-sets/{foreign_id}")
    _test("GET foreign record -> 404", resp_foreign.status_code == 404, f"got {resp_foreign.status_code}")

    # -----------------------------------------------------------------------
    # Test 5: PATCH update
    # -----------------------------------------------------------------------
    print("Test 5: PATCH update")
    resp_patch = client.patch(f"/v1/cut-rule-sets/{created_id}", json={
        "is_active": False,
        "notes": "deactivated for testing",
    })
    _test("PATCH -> 200", resp_patch.status_code == 200, f"got {resp_patch.status_code}")
    patched = resp_patch.json()
    _test("is_active == False after patch", patched.get("is_active") is False)
    _test("notes updated", patched.get("notes") == "deactivated for testing")
    _test("name unchanged", patched.get("name") == "Steel Laser Defaults")

    # -----------------------------------------------------------------------
    # Test 6: DELETE
    # -----------------------------------------------------------------------
    print("Test 6: DELETE")
    resp_del = client.delete(f"/v1/cut-rule-sets/{created_id}")
    _test("DELETE -> 204", resp_del.status_code == 204, f"got {resp_del.status_code}")

    resp_after_del = client.get(f"/v1/cut-rule-sets/{created_id}")
    _test("GET after DELETE -> 404", resp_after_del.status_code == 404, f"got {resp_after_del.status_code}")

    # -----------------------------------------------------------------------
    # Test 7: foreign owner record not modifiable
    # -----------------------------------------------------------------------
    print("Test 7: foreign owner record not modifiable")
    resp_patch_foreign = client.patch(f"/v1/cut-rule-sets/{foreign_id}", json={"is_active": False})
    _test("PATCH foreign -> 404", resp_patch_foreign.status_code == 404, f"got {resp_patch_foreign.status_code}")

    resp_del_foreign = client.delete(f"/v1/cut-rule-sets/{foreign_id}")
    _test("DELETE foreign -> 404", resp_del_foreign.status_code == 404, f"got {resp_del_foreign.status_code}")

    # -----------------------------------------------------------------------
    # Test 8: meta fields stable
    # -----------------------------------------------------------------------
    print("Test 8: machine_code, material_code, thickness_mm meta stability")
    resp_v2 = client.get(f"/v1/cut-rule-sets/{created_id_v2}")
    _test("GET v2 -> 200", resp_v2.status_code == 200)
    v2_body = resp_v2.json()
    _test("machine_code == LASER-A", v2_body.get("machine_code") == "LASER-A")
    _test("material_code == S235", v2_body.get("material_code") == "S235")
    _test("thickness_mm == 12.0", v2_body.get("thickness_mm") == 12.0, f"got {v2_body.get('thickness_mm')}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total = passed + failed
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"[PASS] smoke_h2_e3_t1_cut_rule_set_model: {passed}/{total} tests passed")
        return 0
    else:
        print(f"[FAIL] smoke_h2_e3_t1_cut_rule_set_model: {passed}/{total} passed, {failed} failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
