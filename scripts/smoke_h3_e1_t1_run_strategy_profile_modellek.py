#!/usr/bin/env python3
"""H3-E1-T1 smoke: run strategy profile/version domain bevezetese."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_strategy_profiles import (  # noqa: E402
    RunStrategyProfileError,
    create_run_strategy_profile,
    create_run_strategy_profile_version,
    delete_run_strategy_profile,
    delete_run_strategy_profile_version,
    get_run_strategy_profile,
    get_run_strategy_profile_version,
    list_run_strategy_profile_versions,
    list_run_strategy_profiles,
    update_run_strategy_profile,
    update_run_strategy_profile_version,
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
            "app.run_strategy_profiles": [],
            "app.run_strategy_profile_versions": [],
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
# 1. Strategy profile CRUD
# ===========================================================================

def test_profile_crud() -> None:
    print("\n=== 1. Strategy profile CRUD ===")
    sb = FakeSupabaseClient()

    profile = create_run_strategy_profile(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        strategy_code="AGGRESSIVE-FILL",
        display_name="Aggressive fill strategy",
        description="Maximizes sheet utilization",
    )
    _test("profile created", profile.get("strategy_code") == "AGGRESSIVE-FILL")
    _test("owner correct", profile.get("owner_user_id") == OWNER_A)
    _test("description set", profile.get("description") == "Maximizes sheet utilization")
    _test("lifecycle default draft", profile.get("lifecycle") == "draft")

    profiles = list_run_strategy_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
    )
    _test("list returns 1", len(profiles) == 1)

    got = get_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
    )
    _test("get returns correct", got["id"] == profile["id"])

    updated = update_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
        updates={"display_name": "Updated strategy"},
    )
    _test("update works", updated.get("display_name") == "Updated strategy")

    deleted = delete_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        profile_id=str(profile["id"]),
    )
    _test("delete returns row", deleted["id"] == profile["id"])

    remaining = list_run_strategy_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
    )
    _test("list empty after delete", len(remaining) == 0)


# ===========================================================================
# 2. Version CRUD under profile
# ===========================================================================

def test_version_crud() -> None:
    print("\n=== 2. Strategy version CRUD ===")
    sb = FakeSupabaseClient()

    profile = create_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        strategy_code="FAST-01", display_name="Fast strategy",
    )
    pid = str(profile["id"])

    v1 = create_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid,
        solver_config_jsonb={"time_limit": 30},
        placement_config_jsonb={"rotation_steps": [0, 90]},
        manufacturing_bias_jsonb={"prefer_fewer_sheets": True},
    )
    _test("version created", v1.get("version_no") == 1)
    _test("solver_config set", v1.get("solver_config_jsonb") == {"time_limit": 30})
    _test("placement_config set", v1.get("placement_config_jsonb") == {"rotation_steps": [0, 90]})
    _test("manufacturing_bias set", v1.get("manufacturing_bias_jsonb") == {"prefer_fewer_sheets": True})

    v2 = create_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid,
        solver_config_jsonb={"time_limit": 120},
    )
    _test("version_no auto-increment", v2.get("version_no") == 2)

    v3 = create_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid,
    )
    _test("version_no increments to 3", v3.get("version_no") == 3)

    versions = list_run_strategy_profile_versions(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid,
    )
    _test("list returns 3", len(versions) == 3)

    got = get_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid, version_id=str(v1["id"]),
    )
    _test("get version correct", got["id"] == v1["id"])

    updated = update_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid, version_id=str(v1["id"]),
        updates={"solver_config_jsonb": {"time_limit": 60}},
    )
    _test("version update works", updated.get("solver_config_jsonb") == {"time_limit": 60})

    delete_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid, version_id=str(v3["id"]),
    )
    remaining = list_run_strategy_profile_versions(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid,
    )
    _test("version deleted", len(remaining) == 2)


# ===========================================================================
# 3. Owner boundary: foreign owner cannot access
# ===========================================================================

def test_owner_boundary() -> None:
    print("\n=== 3. Owner boundary ===")
    sb = FakeSupabaseClient()

    profile = create_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        strategy_code="OWNER-TEST", display_name="Owner A strategy",
    )
    pid = str(profile["id"])

    # Owner B cannot get Owner A's profile
    try:
        get_run_strategy_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid,
        )
        _test("foreign owner get rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("foreign owner get rejected", exc.status_code == 404)

    # Owner B cannot list Owner A's profiles
    b_profiles = list_run_strategy_profiles(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
    )
    _test("foreign owner list returns 0", len(b_profiles) == 0)

    # Owner B cannot update Owner A's profile
    try:
        update_run_strategy_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid, updates={"display_name": "hacked"},
        )
        _test("foreign owner update rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("foreign owner update rejected", exc.status_code == 404)

    # Owner B cannot delete Owner A's profile
    try:
        delete_run_strategy_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            profile_id=pid,
        )
        _test("foreign owner delete rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("foreign owner delete rejected", exc.status_code == 404)

    # Version under foreign profile
    v1 = create_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=pid,
    )
    try:
        get_run_strategy_profile_version(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            run_strategy_profile_id=pid, version_id=str(v1["id"]),
        )
        _test("foreign owner version get rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("foreign owner version get rejected", exc.status_code == 404)

    # Owner B cannot create version under Owner A's profile
    try:
        create_run_strategy_profile_version(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            run_strategy_profile_id=pid,
        )
        _test("foreign owner version create rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("foreign owner version create rejected", exc.status_code == 404)


# ===========================================================================
# 4. No scoring or project-selection side effect
# ===========================================================================

def test_no_scoring_selection_scope() -> None:
    print("\n=== 4. No scoring or project-selection scope ===")
    sb = FakeSupabaseClient()

    create_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        strategy_code="SCOPE-CHECK", display_name="Scope check",
    )

    # Check that no scoring or selection tables were touched
    scoring_tables = [
        "app.scoring_profiles",
        "app.scoring_profile_versions",
        "app.project_run_strategy_selection",
        "app.project_scoring_selection",
    ]
    for table_name in scoring_tables:
        writes = [e for e in sb.write_log if e.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    # Check source code for scoring/selection references
    import api.services.run_strategy_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no scoring_profile in service", "scoring_profile" not in source)
    _test("no project_run_strategy_selection in service", "project_run_strategy_selection" not in source)
    _test("no project_scoring_selection in service", "project_scoring_selection" not in source)


# ===========================================================================
# 5. No snapshot-builder or run-creation side effect
# ===========================================================================

def test_no_snapshot_run_side_effect() -> None:
    print("\n=== 5. No snapshot-builder or run-creation side effect ===")
    sb = FakeSupabaseClient()

    profile = create_run_strategy_profile(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        strategy_code="SIDE-CHECK", display_name="Side effect check",
    )
    create_run_strategy_profile_version(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        run_strategy_profile_id=str(profile["id"]),
    )

    snapshot_tables = [
        "app.nesting_runs",
        "app.nesting_run_snapshots",
        "app.run_queue",
        "app.run_logs",
    ]
    for table_name in snapshot_tables:
        writes = [e for e in sb.write_log if e.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    # Check source code for snapshot/run references
    import api.services.run_strategy_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no run_snapshot_builder in service", "run_snapshot_builder" not in source)
    _test("no run_creation in service", "run_creation" not in source)
    _test("no nesting_runs in service", "nesting_runs" not in source)
    _test("no nesting_run_snapshots in service", "nesting_run_snapshots" not in source)


# ===========================================================================
# 6. No catalog-FK world
# ===========================================================================

def test_no_catalog_fk() -> None:
    print("\n=== 6. No catalog-FK world ===")
    migration_path = ROOT / "supabase" / "migrations" / "20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql"
    sql = migration_path.read_text()
    # Strip SQL comments (lines starting with --) to only check DDL statements
    ddl_lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    ddl_only = "\n".join(ddl_lines)
    _test("no machine_catalog FK in DDL", "machine_catalog" not in ddl_only)
    _test("no material_catalog FK in DDL", "material_catalog" not in ddl_only)
    _test("no scoring table in DDL", "scoring" not in ddl_only.lower())
    _test("no project_run_strategy_selection in DDL", "project_run_strategy_selection" not in ddl_only)

    import api.services.run_strategy_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no machine_catalog in service", "machine_catalog" not in source)
    _test("no material_catalog in service", "material_catalog" not in source)


# ===========================================================================
# 7. Strategy domain is separate from run_configs
# ===========================================================================

def test_separate_from_run_configs() -> None:
    print("\n=== 7. Strategy domain separate from run_configs ===")
    import api.services.run_strategy_profiles as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no run_configs table reference in service", "app.run_configs" not in source)
    _test("no run_config import in service", "from api.routes.run_configs" not in source)

    import api.routes.run_strategy_profiles as route_mod
    route_source = Path(route_mod.__file__).read_text()
    _test("no run_configs reference in route", "run_configs" not in route_source)

    # Confirm separate prefix
    from api.routes.run_strategy_profiles import router
    _test("route prefix is /run-strategy-profiles", router.prefix == "/run-strategy-profiles")


# ===========================================================================
# 8. Migration structure validation
# ===========================================================================

def test_migration_structure() -> None:
    print("\n=== 8. Migration structure ===")
    migration_path = ROOT / "supabase" / "migrations" / "20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql"
    sql = migration_path.read_text()

    _test("creates run_strategy_profiles table", "app.run_strategy_profiles" in sql)
    _test("creates run_strategy_profile_versions table", "app.run_strategy_profile_versions" in sql)
    _test("has owner_user_id FK", "references app.profiles(id)" in sql)
    _test("has composite owner constraint", "fk_run_strategy_profile_versions_profile_owner" in sql)
    _test("has RLS enabled for profiles", "alter table app.run_strategy_profiles enable row level security" in sql)
    _test("has RLS enabled for versions", "alter table app.run_strategy_profile_versions enable row level security" in sql)
    _test("has updated_at trigger for profiles", "trg_run_strategy_profiles_set_updated_at" in sql)
    _test("has updated_at trigger for versions", "trg_run_strategy_profile_versions_set_updated_at" in sql)
    _test("has strategy_code non-empty check", "length(btrim(strategy_code))" in sql)
    _test("has display_name non-empty check", "length(btrim(display_name))" in sql)
    _test("has version_no positive check", "version_no > 0" in sql)
    _test("has unique(owner, strategy_code)", "unique (owner_user_id, strategy_code)" in sql)
    _test("has unique(profile_id, version_no)", "unique (run_strategy_profile_id, version_no)" in sql)
    _test("has solver_config_jsonb", "solver_config_jsonb" in sql)
    _test("has placement_config_jsonb", "placement_config_jsonb" in sql)
    _test("has manufacturing_bias_jsonb", "manufacturing_bias_jsonb" in sql)


# ===========================================================================
# 9. Validation: empty fields rejected
# ===========================================================================

def test_validation() -> None:
    print("\n=== 9. Validation ===")
    sb = FakeSupabaseClient()

    try:
        create_run_strategy_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            strategy_code="", display_name="Test",
        )
        _test("empty strategy_code rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("empty strategy_code rejected", exc.status_code == 400)

    try:
        create_run_strategy_profile(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            strategy_code="VALID", display_name="   ",
        )
        _test("whitespace display_name rejected", False, detail="should have raised")
    except RunStrategyProfileError as exc:
        _test("whitespace display_name rejected", exc.status_code == 400)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    print("H3-E1-T1 smoke: run strategy profile/version domain\n")

    test_profile_crud()
    test_version_crud()
    test_owner_boundary()
    test_no_scoring_selection_scope()
    test_no_snapshot_run_side_effect()
    test_no_catalog_fk()
    test_separate_from_run_configs()
    test_migration_structure()
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
