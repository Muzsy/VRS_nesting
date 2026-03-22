#!/usr/bin/env python3
"""H2-E3-T2 smoke: cut contour rules model — owner-scoped CRUD + validation."""

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
from api.routes.cut_contour_rules import router as cut_contour_rules_router
from api.supabase_client import SupabaseHTTPError


# ---------------------------------------------------------------------------
# Fake Supabase client for cut_rule_sets + cut_contour_rules
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.cut_rule_sets: dict[str, dict[str, Any]] = {}
        self.cut_contour_rules: dict[str, dict[str, Any]] = {}

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

    def _get_store(self, table: str) -> dict[str, dict[str, Any]] | None:
        if table == "app.cut_rule_sets":
            return self.cut_rule_sets
        if table == "app.cut_contour_rules":
            return self.cut_contour_rules
        return None

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        store = self._get_store(table)
        if store is None:
            return []

        rows = list(store.values())
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
        store = self._get_store(table)
        if store is None:
            raise RuntimeError(f"unsupported table insert: {table}")

        row = dict(payload)
        row_id = str(row.get("id") or str(uuid4()))
        row["id"] = row_id

        if table == "app.cut_rule_sets":
            for existing in store.values():
                if (
                    existing.get("owner_user_id") == row.get("owner_user_id")
                    and existing.get("name") == row.get("name")
                    and existing.get("version_no") == row.get("version_no")
                ):
                    raise SupabaseHTTPError(
                        "duplicate key value violates unique constraint"
                    )

        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        row.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        store[row_id] = row
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
        store = self._get_store(table)
        if store is None:
            return []

        rows = list(store.values())
        for key, raw_filter in filters.items():
            rows = [row for row in rows if self._matches(row, key, raw_filter)]

        updated: list[dict[str, Any]] = []
        for row in rows:
            row_id = str(row.get("id") or "")
            current = store[row_id]
            current.update(payload)
            updated.append(dict(current))
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        store = self._get_store(table)
        if store is None:
            return

        delete_keys: list[str] = []
        for row_id, row in store.items():
            match = True
            for key, raw_filter in filters.items():
                if not self._matches(row, key, raw_filter):
                    match = False
                    break
            if match:
                delete_keys.append(row_id)

        for key in delete_keys:
            store.pop(key, None)


# ---------------------------------------------------------------------------
# Test app builder
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_OWNER_ID = "00000000-0000-0000-0000-000000000002"


def _build_test_app(fake: FakeSupabaseClient, *, owner_id: str = OWNER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(cut_rule_sets_router, prefix="/v1")
    app.include_router(cut_contour_rules_router, prefix="/v1")
    app.dependency_overrides[get_supabase_client] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=owner_id,
        email="u1@example.com",
        access_token="token-u1",
    )
    return app


def _seed_rule_set(fake: FakeSupabaseClient, *, owner_id: str, name: str = "Test Rules") -> str:
    rs_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    fake.cut_rule_sets[rs_id] = {
        "id": rs_id,
        "owner_user_id": owner_id,
        "name": name,
        "version_no": 1,
        "is_active": True,
        "machine_code": "LASER-A",
        "material_code": "S235",
        "thickness_mm": 10.0,
        "metadata_jsonb": {},
        "created_at": now,
        "updated_at": now,
    }
    return rs_id


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

    # Seed own rule set
    own_rs_id = _seed_rule_set(fake, owner_id=OWNER_ID, name="My Cut Rules")
    # Seed foreign rule set
    foreign_rs_id = _seed_rule_set(fake, owner_id=OTHER_OWNER_ID, name="Foreign Rules")

    BASE = f"/v1/cut-rule-sets/{own_rs_id}/rules"
    FOREIGN_BASE = f"/v1/cut-rule-sets/{foreign_rs_id}/rules"

    # -----------------------------------------------------------------------
    # Test 1: owner-scope create outer rule
    # -----------------------------------------------------------------------
    print("Test 1: owner-scope create outer contour rule")
    resp = client.post(BASE, json={
        "contour_kind": "outer",
        "lead_in_type": "line",
        "lead_in_length_mm": 5.0,
        "lead_out_type": "arc",
        "lead_out_length_mm": 3.0,
        "lead_out_radius_mm": 2.0,
        "sort_order": 1,
    })
    _test("POST outer rule -> 201", resp.status_code == 201, f"got {resp.status_code}")
    body = resp.json()
    outer_rule_id = body.get("id", "")
    _test("contour_kind == outer", body.get("contour_kind") == "outer")
    _test("cut_rule_set_id correct", body.get("cut_rule_set_id") == own_rs_id)
    _test("lead_in_type == line", body.get("lead_in_type") == "line")
    _test("lead_in_length_mm == 5.0", body.get("lead_in_length_mm") == 5.0)
    _test("lead_out_type == arc", body.get("lead_out_type") == "arc")
    _test("feature_class defaults to 'default'", body.get("feature_class") == "default")
    _test("enabled defaults to True", body.get("enabled") is True)

    # -----------------------------------------------------------------------
    # Test 2: create inner rule on same rule set
    # -----------------------------------------------------------------------
    print("Test 2: create inner contour rule on same rule set")
    resp2 = client.post(BASE, json={
        "contour_kind": "inner",
        "feature_class": "hole",
        "lead_in_type": "arc",
        "lead_in_length_mm": 2.0,
        "lead_in_radius_mm": 1.5,
        "lead_out_type": "none",
        "sort_order": 2,
    })
    _test("POST inner rule -> 201", resp2.status_code == 201, f"got {resp2.status_code}")
    body2 = resp2.json()
    inner_rule_id = body2.get("id", "")
    _test("contour_kind == inner", body2.get("contour_kind") == "inner")
    _test("feature_class == hole", body2.get("feature_class") == "hole")
    _test("lead_in_type == arc", body2.get("lead_in_type") == "arc")
    _test("lead_in_radius_mm == 1.5", body2.get("lead_in_radius_mm") == 1.5)
    _test("lead_out_type == none", body2.get("lead_out_type") == "none")

    # -----------------------------------------------------------------------
    # Test 3: list rules scoped to rule set
    # -----------------------------------------------------------------------
    print("Test 3: list is scoped to rule set")
    resp_list = client.get(BASE)
    _test("GET list -> 200", resp_list.status_code == 200)
    items = resp_list.json()
    _test("list returns 2 rules", len(items) == 2, f"got {len(items)}")
    all_set_ids = {item.get("cut_rule_set_id") for item in items}
    _test("all rules belong to same rule set", all_set_ids == {own_rs_id})

    # -----------------------------------------------------------------------
    # Test 4: GET single rule
    # -----------------------------------------------------------------------
    print("Test 4: GET single rule")
    resp_get = client.get(f"{BASE}/{outer_rule_id}")
    _test("GET rule -> 200", resp_get.status_code == 200)
    _test("correct id returned", resp_get.json().get("id") == outer_rule_id)

    # -----------------------------------------------------------------------
    # Test 5: PATCH update
    # -----------------------------------------------------------------------
    print("Test 5: PATCH update")
    resp_patch = client.patch(f"{BASE}/{outer_rule_id}", json={
        "enabled": False,
        "lead_in_type": "arc",
        "lead_in_radius_mm": 4.0,
    })
    _test("PATCH -> 200", resp_patch.status_code == 200, f"got {resp_patch.status_code}")
    patched = resp_patch.json()
    _test("enabled == False after patch", patched.get("enabled") is False)
    _test("lead_in_type == arc after patch", patched.get("lead_in_type") == "arc")
    _test("lead_in_radius_mm == 4.0 after patch", patched.get("lead_in_radius_mm") == 4.0)
    _test("contour_kind unchanged", patched.get("contour_kind") == "outer")

    # -----------------------------------------------------------------------
    # Test 6: DELETE
    # -----------------------------------------------------------------------
    print("Test 6: DELETE")
    resp_del = client.delete(f"{BASE}/{inner_rule_id}")
    _test("DELETE -> 204", resp_del.status_code == 204, f"got {resp_del.status_code}")

    resp_after_del = client.get(f"{BASE}/{inner_rule_id}")
    _test("GET after DELETE -> 404", resp_after_del.status_code == 404, f"got {resp_after_del.status_code}")

    # list should now have 1 rule
    resp_list2 = client.get(BASE)
    _test("list after delete has 1 rule", len(resp_list2.json()) == 1, f"got {len(resp_list2.json())}")

    # -----------------------------------------------------------------------
    # Test 7: cannot create rule under foreign owner's rule set
    # -----------------------------------------------------------------------
    print("Test 7: foreign owner rule set -> 404")
    resp_foreign = client.post(FOREIGN_BASE, json={
        "contour_kind": "outer",
    })
    _test("POST on foreign rule set -> 404", resp_foreign.status_code == 404, f"got {resp_foreign.status_code}")

    # -----------------------------------------------------------------------
    # Test 8: invalid contour_kind rejected
    # -----------------------------------------------------------------------
    print("Test 8: invalid contour_kind rejected")
    resp_bad_kind = client.post(BASE, json={
        "contour_kind": "unknown",
    })
    _test("POST invalid contour_kind -> 400", resp_bad_kind.status_code == 400, f"got {resp_bad_kind.status_code}")
    _test("error mentions contour_kind", "contour_kind" in resp_bad_kind.json().get("detail", ""))

    # -----------------------------------------------------------------------
    # Test 9: invalid lead type rejected
    # -----------------------------------------------------------------------
    print("Test 9: invalid lead type rejected")
    resp_bad_lead = client.post(BASE, json={
        "contour_kind": "outer",
        "lead_in_type": "spiral",
    })
    _test("POST invalid lead_in_type -> 400", resp_bad_lead.status_code == 400, f"got {resp_bad_lead.status_code}")
    _test("error mentions lead_in_type", "lead_in_type" in resp_bad_lead.json().get("detail", ""))

    # -----------------------------------------------------------------------
    # Test 10: negative numeric values rejected
    # -----------------------------------------------------------------------
    print("Test 10: negative numeric values rejected")
    resp_neg = client.post(BASE, json={
        "contour_kind": "outer",
        "lead_in_length_mm": -5.0,
    })
    _test("POST negative lead_in_length_mm -> 400", resp_neg.status_code == 400, f"got {resp_neg.status_code}")
    _test("error mentions positive", "positive" in resp_neg.json().get("detail", "").lower() or "lead_in_length_mm" in resp_neg.json().get("detail", ""))

    resp_neg2 = client.post(BASE, json={
        "contour_kind": "outer",
        "lead_out_radius_mm": -1.0,
    })
    _test("POST negative lead_out_radius_mm -> 400", resp_neg2.status_code == 400, f"got {resp_neg2.status_code}")

    # -----------------------------------------------------------------------
    # Test 11: bad min/max contour length range rejected
    # -----------------------------------------------------------------------
    print("Test 11: bad min/max contour length range rejected")
    resp_range = client.post(BASE, json={
        "contour_kind": "outer",
        "min_contour_length_mm": 100.0,
        "max_contour_length_mm": 50.0,
    })
    _test("POST min > max -> 400", resp_range.status_code == 400, f"got {resp_range.status_code}")
    _test("error mentions min/max", "min_contour_length_mm" in resp_range.json().get("detail", ""))

    # valid min/max should work
    resp_range_ok = client.post(BASE, json={
        "contour_kind": "inner",
        "min_contour_length_mm": 10.0,
        "max_contour_length_mm": 200.0,
        "sort_order": 10,
    })
    _test("POST valid min < max -> 201", resp_range_ok.status_code == 201, f"got {resp_range_ok.status_code}")
    range_body = resp_range_ok.json()
    _test("min_contour_length_mm == 10.0", range_body.get("min_contour_length_mm") == 10.0)
    _test("max_contour_length_mm == 200.0", range_body.get("max_contour_length_mm") == 200.0)

    # -----------------------------------------------------------------------
    # Test 12: multiple rules with different sort_order
    # -----------------------------------------------------------------------
    print("Test 12: multiple rules with different sort_order")
    resp_list3 = client.get(BASE)
    items3 = resp_list3.json()
    sort_orders = [item.get("sort_order") for item in items3]
    _test("multiple rules exist", len(items3) >= 2, f"got {len(items3)}")
    _test("sort_orders are present", all(so is not None for so in sort_orders))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total = passed + failed
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"[PASS] smoke_h2_e3_t2_cut_contour_rules_model: {passed}/{total} tests passed")
        return 0
    else:
        print(f"[FAIL] smoke_h2_e3_t2_cut_contour_rules_model: {passed}/{total} passed, {failed} failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
