#!/usr/bin/env python3
"""H3-E1-T3 smoke: project-level strategy es scoring selection truth."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.project_strategy_scoring_selection import (  # noqa: E402
    ProjectStrategyScoringSelectionError,
    delete_project_run_strategy_selection,
    delete_project_scoring_selection,
    get_project_run_strategy_selection,
    get_project_scoring_selection,
    set_project_run_strategy_selection,
    set_project_scoring_selection,
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
            "app.projects": [],
            "app.run_strategy_profile_versions": [],
            "app.scoring_profile_versions": [],
            "app.project_run_strategy_selection": [],
            "app.project_scoring_selection": [],
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


def _seed_project(sb: FakeSupabaseClient, owner: str) -> str:
    pid = str(uuid4())
    sb.tables["app.projects"].append({
        "id": pid,
        "owner_user_id": owner,
        "lifecycle": "active",
    })
    return pid


def _seed_strategy_version(sb: FakeSupabaseClient, owner: str, *, is_active: bool = True) -> str:
    vid = str(uuid4())
    profile_id = str(uuid4())
    sb.tables["app.run_strategy_profile_versions"].append({
        "id": vid,
        "run_strategy_profile_id": profile_id,
        "owner_user_id": owner,
        "version_no": 1,
        "lifecycle": "draft",
        "is_active": is_active,
    })
    return vid


def _seed_scoring_version(sb: FakeSupabaseClient, owner: str, *, is_active: bool = True) -> str:
    vid = str(uuid4())
    profile_id = str(uuid4())
    sb.tables["app.scoring_profile_versions"].append({
        "id": vid,
        "scoring_profile_id": profile_id,
        "owner_user_id": owner,
        "version_no": 1,
        "lifecycle": "draft",
        "is_active": is_active,
    })
    return vid


# ===========================================================================
# 1. Strategy selection: set / get / overwrite / delete
# ===========================================================================

def test_strategy_selection_crud() -> None:
    print("\n=== 1. Strategy selection CRUD ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    sv1 = _seed_strategy_version(sb, OWNER_A)
    sv2 = _seed_strategy_version(sb, OWNER_A)

    # SET (create)
    result = set_project_run_strategy_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id, active_run_strategy_profile_version_id=sv1,
    )
    _test("strategy set creates selection", result["selection"]["active_run_strategy_profile_version_id"] == sv1)
    _test("strategy set was_existing=False", result["was_existing_selection"] is False)

    # GET
    result = get_project_run_strategy_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id,
    )
    _test("strategy get returns correct version", result["selection"]["active_run_strategy_profile_version_id"] == sv1)

    # OVERWRITE (replace)
    result = set_project_run_strategy_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id, active_run_strategy_profile_version_id=sv2,
    )
    _test("strategy overwrite works", result["selection"]["active_run_strategy_profile_version_id"] == sv2)
    _test("strategy overwrite was_existing=True", result["was_existing_selection"] is True)

    # Verify only one row
    sel_rows = sb.tables["app.project_run_strategy_selection"]
    project_rows = [r for r in sel_rows if r.get("project_id") == project_id]
    _test("only one strategy selection per project", len(project_rows) == 1)

    # DELETE
    result = delete_project_run_strategy_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id,
    )
    _test("strategy delete returns selection", result["selection"]["active_run_strategy_profile_version_id"] == sv2)

    # GET after delete -> 404
    try:
        get_project_run_strategy_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id,
        )
        _test("strategy get after delete -> 404", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("strategy get after delete -> 404", exc.status_code == 404)


# ===========================================================================
# 2. Scoring selection: set / get / overwrite / delete
# ===========================================================================

def test_scoring_selection_crud() -> None:
    print("\n=== 2. Scoring selection CRUD ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    sv1 = _seed_scoring_version(sb, OWNER_A)
    sv2 = _seed_scoring_version(sb, OWNER_A)

    # SET (create)
    result = set_project_scoring_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id, active_scoring_profile_version_id=sv1,
    )
    _test("scoring set creates selection", result["selection"]["active_scoring_profile_version_id"] == sv1)
    _test("scoring set was_existing=False", result["was_existing_selection"] is False)

    # GET
    result = get_project_scoring_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id,
    )
    _test("scoring get returns correct version", result["selection"]["active_scoring_profile_version_id"] == sv1)

    # OVERWRITE (replace)
    result = set_project_scoring_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id, active_scoring_profile_version_id=sv2,
    )
    _test("scoring overwrite works", result["selection"]["active_scoring_profile_version_id"] == sv2)
    _test("scoring overwrite was_existing=True", result["was_existing_selection"] is True)

    # Verify only one row
    sel_rows = sb.tables["app.project_scoring_selection"]
    project_rows = [r for r in sel_rows if r.get("project_id") == project_id]
    _test("only one scoring selection per project", len(project_rows) == 1)

    # DELETE
    result = delete_project_scoring_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id,
    )
    _test("scoring delete returns selection", result["selection"]["active_scoring_profile_version_id"] == sv2)

    # GET after delete -> 404
    try:
        get_project_scoring_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id,
        )
        _test("scoring get after delete -> 404", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("scoring get after delete -> 404", exc.status_code == 404)


# ===========================================================================
# 3. Foreign owner project rejected
# ===========================================================================

def test_foreign_owner_project() -> None:
    print("\n=== 3. Foreign owner project rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    sv = _seed_strategy_version(sb, OWNER_A)
    scv = _seed_scoring_version(sb, OWNER_A)

    # Owner B cannot set strategy on Owner A's project
    try:
        set_project_run_strategy_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            project_id=project_id, active_run_strategy_profile_version_id=sv,
        )
        _test("foreign project strategy set rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("foreign project strategy set rejected", exc.status_code == 404)

    # Owner B cannot set scoring on Owner A's project
    try:
        set_project_scoring_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_B,
            project_id=project_id, active_scoring_profile_version_id=scv,
        )
        _test("foreign project scoring set rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("foreign project scoring set rejected", exc.status_code == 404)


# ===========================================================================
# 4. Foreign owner strategy/scoring version rejected
# ===========================================================================

def test_foreign_owner_version() -> None:
    print("\n=== 4. Foreign owner version rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)

    # Strategy version owned by B
    sv_b = _seed_strategy_version(sb, OWNER_B)
    try:
        set_project_run_strategy_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id, active_run_strategy_profile_version_id=sv_b,
        )
        _test("foreign strategy version rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("foreign strategy version rejected", exc.status_code == 403)

    # Scoring version owned by B
    scv_b = _seed_scoring_version(sb, OWNER_B)
    try:
        set_project_scoring_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id, active_scoring_profile_version_id=scv_b,
        )
        _test("foreign scoring version rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("foreign scoring version rejected", exc.status_code == 403)


# ===========================================================================
# 5. Inactive version rejected
# ===========================================================================

def test_inactive_version_rejected() -> None:
    print("\n=== 5. Inactive version rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)

    # Inactive strategy version
    sv_inactive = _seed_strategy_version(sb, OWNER_A, is_active=False)
    try:
        set_project_run_strategy_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id, active_run_strategy_profile_version_id=sv_inactive,
        )
        _test("inactive strategy version rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("inactive strategy version rejected", exc.status_code == 400)

    # Inactive scoring version
    scv_inactive = _seed_scoring_version(sb, OWNER_A, is_active=False)
    try:
        set_project_scoring_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id, active_scoring_profile_version_id=scv_inactive,
        )
        _test("inactive scoring version rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("inactive scoring version rejected", exc.status_code == 400)


# ===========================================================================
# 6. No run_batches, run_evaluations, ranking, snapshot side effect
# ===========================================================================

def test_no_forbidden_side_effects() -> None:
    print("\n=== 6. No forbidden side effects ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    sv = _seed_strategy_version(sb, OWNER_A)
    scv = _seed_scoring_version(sb, OWNER_A)

    set_project_run_strategy_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id, active_run_strategy_profile_version_id=sv,
    )
    set_project_scoring_selection(
        supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
        project_id=project_id, active_scoring_profile_version_id=scv,
    )

    forbidden_tables = [
        "app.run_batches",
        "app.run_batch_items",
        "app.run_evaluations",
        "app.run_ranking_results",
        "app.nesting_run_snapshots",
        "app.nesting_runs",
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.run_manufacturing_metrics",
    ]
    for table_name in forbidden_tables:
        writes = [e for e in sb.write_log if e.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    # Source code audit
    import api.services.project_strategy_scoring_selection as svc_mod
    source = Path(svc_mod.__file__).read_text()
    _test("no run_batches in service", "run_batches" not in source)
    _test("no run_evaluations in service", "run_evaluations" not in source)
    _test("no run_ranking in service", "run_ranking" not in source)
    _test("no nesting_run_snapshots in service", "nesting_run_snapshots" not in source)
    _test("no run_manufacturing in service", "run_manufacturing" not in source)


# ===========================================================================
# 7. Migration structure validation
# ===========================================================================

def test_migration_structure() -> None:
    print("\n=== 7. Migration structure ===")
    migration_path = ROOT / "supabase" / "migrations" / "20260324120000_h3_e1_t3_project_level_selectionok.sql"
    sql = migration_path.read_text()

    _test("creates project_run_strategy_selection table", "app.project_run_strategy_selection" in sql)
    _test("creates project_scoring_selection table", "app.project_scoring_selection" in sql)
    _test("project_id PK strategy", "project_id uuid primary key references app.projects(id)" in sql)
    _test("FK to run_strategy_profile_versions", "references app.run_strategy_profile_versions(id)" in sql)
    _test("FK to scoring_profile_versions", "references app.scoring_profile_versions(id)" in sql)
    _test("selected_by FK", "references app.profiles(id)" in sql)
    _test("RLS on strategy selection", "alter table app.project_run_strategy_selection enable row level security" in sql)
    _test("RLS on scoring selection", "alter table app.project_scoring_selection enable row level security" in sql)
    _test("strategy select policy", "h3_e1_t3_project_run_strategy_selection_select_owner" in sql)
    _test("scoring select policy", "h3_e1_t3_project_scoring_selection_select_owner" in sql)
    _test("uses is_project_owner", "app.is_project_owner(project_id)" in sql)

    # No forbidden tables
    ddl_lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    ddl_only = "\n".join(ddl_lines)
    _test("no run_batches in DDL", "run_batches" not in ddl_only)
    _test("no run_evaluations in DDL", "run_evaluations" not in ddl_only)
    _test("no run_ranking in DDL", "run_ranking" not in ddl_only)
    _test("no nesting_run_snapshots in DDL", "nesting_run_snapshots" not in ddl_only)


# ===========================================================================
# 8. Route structure validation
# ===========================================================================

def test_route_structure() -> None:
    print("\n=== 8. Route structure ===")
    import api.routes.project_strategy_scoring_selection as route_mod
    route_source = Path(route_mod.__file__).read_text()

    _test("no run_batches in route", "run_batches" not in route_source)
    _test("no run_evaluations in route", "run_evaluations" not in route_source)
    _test("no nesting_run_snapshots in route", "nesting_run_snapshots" not in route_source)

    from api.routes.project_strategy_scoring_selection import strategy_router, scoring_router
    _test("strategy route prefix", strategy_router.prefix == "/projects/{project_id}/run-strategy-selection")
    _test("scoring route prefix", scoring_router.prefix == "/projects/{project_id}/scoring-selection")


# ===========================================================================
# 9. Nonexistent version rejected
# ===========================================================================

def test_nonexistent_version() -> None:
    print("\n=== 9. Nonexistent version rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    fake_version = str(uuid4())

    try:
        set_project_run_strategy_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id, active_run_strategy_profile_version_id=fake_version,
        )
        _test("nonexistent strategy version rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("nonexistent strategy version rejected", exc.status_code == 404)

    try:
        set_project_scoring_selection(
            supabase=sb, access_token=TOKEN, owner_user_id=OWNER_A,
            project_id=project_id, active_scoring_profile_version_id=fake_version,
        )
        _test("nonexistent scoring version rejected", False, detail="should have raised")
    except ProjectStrategyScoringSelectionError as exc:
        _test("nonexistent scoring version rejected", exc.status_code == 404)


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    print("H3-E1-T3 smoke: project-level strategy es scoring selection\n")

    test_strategy_selection_crud()
    test_scoring_selection_crud()
    test_foreign_owner_project()
    test_foreign_owner_version()
    test_inactive_version_rejected()
    test_no_forbidden_side_effects()
    test_migration_structure()
    test_route_structure()
    test_nonexistent_version()

    total = passed + failed
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        sys.exit(1)
    else:
        print("SMOKE PASS")
        sys.exit(0)
