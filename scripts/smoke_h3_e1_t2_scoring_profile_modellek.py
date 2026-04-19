#!/usr/bin/env python3
"""H3-E1-T2 smoke: scoring profile/version domain bevezetese."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.scoring_profiles import (  # noqa: E402
    ScoringProfileError,
    create_scoring_profile,
    create_scoring_profile_version,
    delete_scoring_profile,
    delete_scoring_profile_version,
    get_scoring_profile,
    get_scoring_profile_version,
    list_scoring_profile_versions,
    list_scoring_profiles,
    update_scoring_profile,
    update_scoring_profile_version,
)

passed = 0
failed = 0


def _test(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK]   {label}")
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.scoring_profiles": [],
            "app.scoring_profile_versions": [],
        }
        self.write_log: list[dict[str, Any]] = []

    @staticmethod
    def _match_filter(value: Any, raw_filter: str) -> bool:
        normalized = raw_filter.strip()
        text = "" if value is None else str(value)
        if normalized.startswith("eq."):
            token = normalized[3:]
            low = token.lower()
            if low == "true":
                return bool(value) is True
            if low == "false":
                return bool(value) is False
            return text == token
        if normalized.startswith("neq."):
            return text != normalized[4:]
        return True

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = [dict(item) for item in self.tables.get(table, [])]
        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._match_filter(row.get(key), raw_filter)]

        order_clause = params.get("order", "").strip()
        if order_clause:
            for token in reversed([p.strip() for p in order_clause.split(",") if p.strip()]):
                col = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda r, c=col: str(r.get(c) or ""), reverse=reverse)

        limit_raw = params.get("limit", "")
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload)
        if "id" not in row:
            row["id"] = str(uuid4())
        self.tables.setdefault(table, []).append(row)
        self.write_log.append({"op": "insert", "table": table, "payload": row})
        return row

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        meta_keys = {"select", "order", "limit", "offset"}
        updated: list[dict[str, Any]] = []
        for row in self.tables.get(table, []):
            match = True
            for key, raw_filter in filters.items():
                if key in meta_keys:
                    continue
                if not self._match_filter(row.get(key), raw_filter):
                    match = False
                    break
            if match:
                row.update(payload)
                updated.append(dict(row))
        self.write_log.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_log.append({"op": "delete", "table": table, "filters": filters})
        meta_keys = {"select", "order", "limit", "offset"}
        rows = self.tables.get(table, [])
        remaining = []
        for row in rows:
            keep = False
            for key, raw_filter in filters.items():
                if key in meta_keys:
                    continue
                if not self._match_filter(row.get(key), raw_filter):
                    keep = True
                    break
            if keep:
                remaining.append(row)
        self.tables[table] = remaining


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OWNER_A = str(uuid4())
OWNER_B = str(uuid4())
TOKEN = "fake-token"


# ===========================================================================
# 1. Scoring profile CRUD
# ===========================================================================

def test_profile_crud() -> None:
    print("\n=== 1. Scoring profile CRUD ===")
    sb = FakeSupabaseClient()

    profile = create_scoring_profile(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        name="Default scoring",
        description="Standard scoring weights",
    )
    _test("profile created", profile.get("name") == "Default scoring")
    _test("owner correct", profile.get("owner_user_id") == OWNER_A)
    _test("description set", profile.get("description") == "Standard scoring weights")
    _test("lifecycle default draft", profile.get("lifecycle") == "draft")

    profiles = list_scoring_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
    )
    _test("list returns 1", len(profiles) == 1)

    got = get_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
    )
    _test("get returns correct", got["id"] == profile["id"])

    updated = update_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
        updates={"name": "Updated scoring"},
    )
    _test("update works", updated.get("name") == "Updated scoring")

    deleted = delete_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
    )
    _test("delete returns row", deleted["id"] == profile["id"])

    remaining = list_scoring_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
    )
    _test("list empty after delete", len(remaining) == 0)


# ===========================================================================
# 2. Version CRUD + JSON payloads persisted
# ===========================================================================

def test_version_crud() -> None:
    print("\n=== 2. Scoring version CRUD + JSON payloads ===")
    sb = FakeSupabaseClient()

    profile = create_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        name="Scoring V", description=None,
    )
    pid = str(profile["id"])

    weights = {
        "utilization_weight": 0.35,
        "unplaced_penalty": 0.20,
        "sheet_count_penalty": 0.10,
        "remnant_value_weight": 0.10,
        "process_time_penalty": 0.10,
        "priority_fulfilment_weight": 0.10,
        "inventory_consumption_penalty": 0.05,
    }
    tie_breaker = {"primary": "utilization", "secondary": "sheet_count"}
    threshold = {"min_utilization": 0.60, "max_unplaced_ratio": 0.05}

    v1 = create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid,
        weights_jsonb=weights,
        tie_breaker_jsonb=tie_breaker,
        threshold_jsonb=threshold,
    )
    _test("version created", v1.get("version_no") == 1)
    _test("weights_jsonb persisted", v1.get("weights_jsonb") == weights)
    _test("tie_breaker_jsonb persisted", v1.get("tie_breaker_jsonb") == tie_breaker)
    _test("threshold_jsonb persisted", v1.get("threshold_jsonb") == threshold)
    _test("is_active default true", v1.get("is_active") is True)

    v2 = create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid,
        weights_jsonb={"utilization_weight": 0.50},
    )
    _test("version_no auto-increment", v2.get("version_no") == 2)

    v3 = create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid,
    )
    _test("version_no increments to 3", v3.get("version_no") == 3)

    versions = list_scoring_profile_versions(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid,
    )
    _test("list returns 3", len(versions) == 3)

    got = get_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid, version_id=str(v1["id"]),
    )
    _test("get version correct", got["id"] == v1["id"])
    _test("get version weights readback", got.get("weights_jsonb") == weights)

    updated = update_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid, version_id=str(v1["id"]),
        updates={"weights_jsonb": {"utilization_weight": 0.99}},
    )
    _test("version update works", updated.get("weights_jsonb") == {"utilization_weight": 0.99})

    delete_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid, version_id=str(v3["id"]),
    )
    remaining = list_scoring_profile_versions(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid,
    )
    _test("version deleted", len(remaining) == 2)


# ===========================================================================
# 3. Owner boundary: foreign owner cannot access
# ===========================================================================

def test_owner_boundary() -> None:
    print("\n=== 3. Owner boundary ===")
    sb = FakeSupabaseClient()

    profile = create_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        name="Owner A scoring",
    )
    pid = str(profile["id"])

    # Owner B cannot get Owner A's profile
    try:
        get_scoring_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid,
        )
        _test("foreign owner get rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("foreign owner get rejected", exc.status_code == 404)

    # Owner B cannot list Owner A's profiles
    b_profiles = list_scoring_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
    )
    _test("foreign owner list returns 0", len(b_profiles) == 0)

    # Owner B cannot update Owner A's profile
    try:
        update_scoring_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid, updates={"name": "hacked"},
        )
        _test("foreign owner update rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("foreign owner update rejected", exc.status_code == 404)

    # Owner B cannot delete Owner A's profile
    try:
        delete_scoring_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid,
        )
        _test("foreign owner delete rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("foreign owner delete rejected", exc.status_code == 404)

    # Version under foreign profile
    v1 = create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=pid,
    )
    try:
        get_scoring_profile_version(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            scoring_profile_id=pid, version_id=str(v1["id"]),
        )
        _test("foreign owner version get rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("foreign owner version get rejected", exc.status_code == 404)

    # Owner B cannot create version under Owner A's profile
    try:
        create_scoring_profile_version(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            scoring_profile_id=pid,
        )
        _test("foreign owner version create rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("foreign owner version create rejected", exc.status_code == 404)


# ===========================================================================
# 4. No project_scoring_selection truth
# ===========================================================================

def test_no_project_scoring_selection() -> None:
    print("\n=== 4. No project_scoring_selection truth ===")
    sb = FakeSupabaseClient()

    profile = create_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        name="Selection scope check",
    )
    create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=str(profile["id"]),
    )

    # Check that no selection tables were touched
    selection_tables = [
        "app.project_scoring_selection",
        "app.project_run_strategy_selection",
    ]
    for table_name in selection_tables:
        writes = [e for e in sb.write_log if e.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    # Check source code
    import api.services.scoring_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no project_scoring_selection in service", "project_scoring_selection" not in source)
    _test("no project_run_strategy_selection in service", "project_run_strategy_selection" not in source)


# ===========================================================================
# 5. No run_evaluations, ranking or comparison scope
# ===========================================================================

def test_no_evaluation_ranking_scope() -> None:
    print("\n=== 5. No run_evaluations, ranking or comparison scope ===")
    sb = FakeSupabaseClient()

    profile = create_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        name="Eval scope check",
    )
    create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=str(profile["id"]),
    )

    eval_tables = [
        "app.run_evaluations",
        "app.run_ranking_results",
        "app.run_batches",
        "app.run_batch_items",
    ]
    for table_name in eval_tables:
        writes = [e for e in sb.write_log if e.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    # Check source code for eval/ranking references
    import api.services.scoring_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no run_evaluations in service", "run_evaluations" not in source)
    _test("no run_ranking in service", "run_ranking" not in source)
    _test("no total_score in service", "total_score" not in source)
    _test("no run_batches in service", "run_batches" not in source)


# ===========================================================================
# 6. No H2 manufacturing truth table write
# ===========================================================================

def test_no_h2_manufacturing_write() -> None:
    print("\n=== 6. No H2 manufacturing truth table write ===")
    sb = FakeSupabaseClient()

    profile = create_scoring_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        name="H2 boundary check",
    )
    create_scoring_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        scoring_profile_id=str(profile["id"]),
    )

    h2_tables = [
        "app.run_manufacturing_metrics",
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.manufacturing_profiles",
        "app.manufacturing_profile_versions",
    ]
    for table_name in h2_tables:
        writes = [e for e in sb.write_log if e.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    import api.services.scoring_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no run_manufacturing in service", "run_manufacturing" not in source)
    _test("no manufacturing_profiles in service", "manufacturing_profiles" not in source)


# ===========================================================================
# 7. Migration structure validation
# ===========================================================================

def test_migration_structure() -> None:
    print("\n=== 7. Migration structure ===")
    migration_path = ROOT / "supabase" / "migrations" / "20260324110000_h3_e1_t2_scoring_profile_modellek.sql"
    sql = migration_path.read_text()

    _test("creates scoring_profiles table", "app.scoring_profiles" in sql)
    _test("creates scoring_profile_versions table", "app.scoring_profile_versions" in sql)
    _test("has owner_user_id FK", "references app.profiles(id)" in sql)
    _test("has composite owner constraint", "fk_scoring_profile_versions_profile_owner" in sql)
    _test("has RLS enabled for profiles", "alter table app.scoring_profiles enable row level security" in sql)
    _test("has RLS enabled for versions", "alter table app.scoring_profile_versions enable row level security" in sql)
    _test("has updated_at trigger for profiles", "trg_scoring_profiles_set_updated_at" in sql)
    _test("has updated_at trigger for versions", "trg_scoring_profile_versions_set_updated_at" in sql)
    _test("has name non-empty check", "length(btrim(name))" in sql)
    _test("has version_no positive check", "version_no > 0" in sql)
    _test("has unique(owner, name)", "unique (owner_user_id, name)" in sql)
    _test("has unique(profile_id, version_no)", "unique (scoring_profile_id, version_no)" in sql)
    _test("has weights_jsonb", "weights_jsonb" in sql)
    _test("has tie_breaker_jsonb", "tie_breaker_jsonb" in sql)
    _test("has threshold_jsonb", "threshold_jsonb" in sql)
    _test("has is_active", "is_active" in sql)

    # Strip SQL comments to only check DDL
    ddl_lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    ddl_only = "\n".join(ddl_lines)
    _test("no project_scoring_selection in DDL", "project_scoring_selection" not in ddl_only)
    _test("no run_evaluations in DDL", "run_evaluations" not in ddl_only)
    _test("no run_ranking in DDL", "run_ranking" not in ddl_only)
    _test("no run_manufacturing in DDL", "run_manufacturing" not in ddl_only)


# ===========================================================================
# 8. Route structure validation
# ===========================================================================

def test_route_structure() -> None:
    print("\n=== 8. Route structure ===")
    import api.routes.scoring_profiles as route_mod
    route_source = Path(route_mod.__file__).read_text()
    _test("no run_evaluations in route", "run_evaluations" not in route_source)
    _test("no project_scoring_selection in route", "project_scoring_selection" not in route_source)
    _test("no run_manufacturing in route", "run_manufacturing" not in route_source)

    from api.routes.scoring_profiles import router
    _test("route prefix is /scoring-profiles", router.prefix == "/scoring-profiles")


# ===========================================================================
# 9. Validation: empty fields rejected
# ===========================================================================

def test_validation() -> None:
    print("\n=== 9. Validation ===")
    sb = FakeSupabaseClient()

    try:
        create_scoring_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            name="",
        )
        _test("empty name rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("empty name rejected", exc.status_code == 400)

    try:
        create_scoring_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            name="   ",
        )
        _test("whitespace name rejected", False, detail="should have raised")
    except ScoringProfileError as exc:
        _test("whitespace name rejected", exc.status_code == 400)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    print("H3-E1-T2 smoke: scoring profile/version domain\n")

    test_profile_crud()
    test_version_crud()
    test_owner_boundary()
    test_no_project_scoring_selection()
    test_no_evaluation_ranking_scope()
    test_no_h2_manufacturing_write()
    test_migration_structure()
    test_route_structure()
    test_validation()

    total = passed + failed
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        sys.exit(1)
    else:
        print("SMOKE PASS")
        sys.exit(0)
