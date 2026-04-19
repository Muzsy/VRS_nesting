#!/usr/bin/env python3
"""H3-E2-T1 smoke: run batch model truth + item management."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_batches import (  # noqa: E402
    RunBatchError,
    attach_run_batch_item,
    create_run_batch,
    delete_run_batch,
    get_run_batch,
    list_run_batch_items,
    list_run_batches,
    remove_run_batch_item,
)
from api.supabase_client import SupabaseHTTPError  # noqa: E402


passed = 0
failed = 0


def _test(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK]   {label}")
    else:
        failed += 1
        message = f"  [FAIL] {label}"
        if detail:
            message += f" -- {detail}"
        print(message, file=sys.stderr)


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.projects": [],
            "app.nesting_runs": [],
            "app.run_batches": [],
            "app.run_batch_items": [],
            "app.run_strategy_profile_versions": [],
            "app.scoring_profile_versions": [],
        }
        self.write_log: list[dict[str, Any]] = []

    @staticmethod
    def _match_filter(value: Any, raw_filter: str) -> bool:
        normalized = str(raw_filter or "").strip()
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
            for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
                col = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda r, c=col: str(r.get(c) or ""), reverse=reverse)

        limit_raw = str(params.get("limit", "")).strip()
        if limit_raw:
            rows = rows[: int(limit_raw)]

        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)

        if table == "app.run_batch_items":
            batch_id = str(row.get("batch_id") or "").strip()
            run_id = str(row.get("run_id") or "").strip()
            for existing in self.tables.get(table, []):
                if str(existing.get("batch_id") or "").strip() == batch_id and str(existing.get("run_id") or "").strip() == run_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint run_batch_items_pkey")

        if "id" not in row and table in {"app.run_batches", "app.nesting_runs"}:
            row["id"] = str(uuid4())

        self.tables.setdefault(table, []).append(row)
        self.write_log.append({"op": "insert", "table": table, "payload": dict(row)})
        return dict(row)

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        _ = access_token
        updated: list[dict[str, Any]] = []
        meta_keys = {"select", "order", "limit", "offset"}

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

        self.write_log.append({"op": "update", "table": table, "payload": dict(payload), "filters": dict(filters)})
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        meta_keys = {"select", "order", "limit", "offset"}
        rows = self.tables.get(table, [])
        remaining: list[dict[str, Any]] = []

        for row in rows:
            match = True
            for key, raw_filter in filters.items():
                if key in meta_keys:
                    continue
                if not self._match_filter(row.get(key), raw_filter):
                    match = False
                    break
            if not match:
                remaining.append(row)

        self.tables[table] = remaining
        self.write_log.append({"op": "delete", "table": table, "filters": dict(filters)})


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


def _seed_run(sb: FakeSupabaseClient, project_id: str, requested_by: str) -> str:
    rid = str(uuid4())
    sb.tables["app.nesting_runs"].append({
        "id": rid,
        "project_id": project_id,
        "requested_by": requested_by,
        "status": "queued",
    })
    return rid


def _seed_strategy_version(sb: FakeSupabaseClient, owner: str, *, is_active: bool = True) -> str:
    vid = str(uuid4())
    sb.tables["app.run_strategy_profile_versions"].append({
        "id": vid,
        "run_strategy_profile_id": str(uuid4()),
        "owner_user_id": owner,
        "version_no": 1,
        "lifecycle": "draft",
        "is_active": is_active,
    })
    return vid


def _seed_scoring_version(sb: FakeSupabaseClient, owner: str, *, is_active: bool = True) -> str:
    vid = str(uuid4())
    sb.tables["app.scoring_profile_versions"].append({
        "id": vid,
        "scoring_profile_id": str(uuid4()),
        "owner_user_id": owner,
        "version_no": 1,
        "lifecycle": "draft",
        "is_active": is_active,
    })
    return vid


def test_batch_crud() -> None:
    print("\n=== 1. Batch CRUD ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)

    b1 = create_run_batch(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_kind="comparison",
        notes="batch one",
    )
    b2 = create_run_batch(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_kind="comparison",
        notes="batch two",
    )
    bid1 = str(b1["batch"]["id"])
    bid2 = str(b2["batch"]["id"])

    listed = list_run_batches(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
    )
    _test("batch list total=2", int(listed["total"]) == 2)
    listed_ids = {str(row.get("id") or "") for row in listed["items"]}
    _test("batch list contains first", bid1 in listed_ids)
    _test("batch list contains second", bid2 in listed_ids)

    got = get_run_batch(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=bid1,
    )
    _test("batch get works", str(got["batch"].get("id") or "") == bid1)

    delete_run_batch(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=bid1,
    )

    try:
        get_run_batch(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=bid1,
        )
        _test("batch get after delete -> 404", False, detail="should have raised")
    except RunBatchError as exc:
        _test("batch get after delete -> 404", exc.status_code == 404)


def test_attach_list_remove_item() -> None:
    print("\n=== 2. Batch item attach/list/remove ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    run_id = _seed_run(sb, project_id, OWNER_A)
    strategy_version_id = _seed_strategy_version(sb, OWNER_A)
    scoring_version_id = _seed_scoring_version(sb, OWNER_A)

    batch_result = create_run_batch(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_kind="comparison",
        notes=None,
    )
    batch_id = str(batch_result["batch"]["id"])

    attach_result = attach_run_batch_item(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        run_id=run_id,
        candidate_label="baseline",
        strategy_profile_version_id=strategy_version_id,
        scoring_profile_version_id=str(scoring_version_id),
    )
    item = attach_result["item"]
    _test("item attach stores run_id", str(item.get("run_id") or "") == run_id)
    _test("item attach stores candidate label", str(item.get("candidate_label") or "") == "baseline")

    listed = list_run_batch_items(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    _test("item list total=1", int(listed["total"]) == 1)

    remove_run_batch_item(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        run_id=run_id,
    )
    listed_after = list_run_batch_items(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    _test("item list empty after remove", int(listed_after["total"]) == 0)


def test_duplicate_item_rejected() -> None:
    print("\n=== 3. Duplicate batch item rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    run_id = _seed_run(sb, project_id, OWNER_A)
    batch_id = str(
        create_run_batch(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_kind="comparison",
            notes=None,
        )["batch"]["id"]
    )

    attach_run_batch_item(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        run_id=run_id,
        candidate_label=None,
        strategy_profile_version_id=None,
        scoring_profile_version_id=None,
    )

    try:
        attach_run_batch_item(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
            run_id=run_id,
            candidate_label=None,
            strategy_profile_version_id=None,
            scoring_profile_version_id=None,
        )
        _test("duplicate attach rejected", False, detail="should have raised")
    except RunBatchError as exc:
        _test("duplicate attach rejected", exc.status_code == 409)


def test_foreign_project_run_rejected() -> None:
    print("\n=== 4. Foreign project run rejected ===")
    sb = FakeSupabaseClient()
    project_a = _seed_project(sb, OWNER_A)
    project_b = _seed_project(sb, OWNER_A)
    run_b = _seed_run(sb, project_b, OWNER_A)

    batch_id = str(
        create_run_batch(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_a,
            batch_kind="comparison",
            notes=None,
        )["batch"]["id"]
    )

    try:
        attach_run_batch_item(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_a,
            batch_id=batch_id,
            run_id=run_b,
            candidate_label=None,
            strategy_profile_version_id=None,
            scoring_profile_version_id=None,
        )
        _test("foreign project run rejected", False, detail="should have raised")
    except RunBatchError as exc:
        _test("foreign project run rejected", exc.status_code == 403)


def test_foreign_owner_versions_rejected() -> None:
    print("\n=== 5. Foreign owner strategy/scoring rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    run_id = _seed_run(sb, project_id, OWNER_A)
    strategy_b = _seed_strategy_version(sb, OWNER_B)
    scoring_b = _seed_scoring_version(sb, OWNER_B)

    batch_id = str(
        create_run_batch(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_kind="comparison",
            notes=None,
        )["batch"]["id"]
    )

    try:
        attach_run_batch_item(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
            run_id=run_id,
            candidate_label=None,
            strategy_profile_version_id=strategy_b,
            scoring_profile_version_id=None,
        )
        _test("foreign strategy version rejected", False, detail="should have raised")
    except RunBatchError as exc:
        _test("foreign strategy version rejected", exc.status_code == 403)

    try:
        attach_run_batch_item(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
            run_id=run_id,
            candidate_label=None,
            strategy_profile_version_id=None,
            scoring_profile_version_id=scoring_b,
        )
        _test("foreign scoring version rejected", False, detail="should have raised")
    except RunBatchError as exc:
        _test("foreign scoring version rejected", exc.status_code == 403)


def test_inactive_versions_rejected() -> None:
    print("\n=== 6. Inactive strategy/scoring rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    run_id = _seed_run(sb, project_id, OWNER_A)
    strategy_inactive = _seed_strategy_version(sb, OWNER_A, is_active=False)
    scoring_inactive = _seed_scoring_version(sb, OWNER_A, is_active=False)

    batch_id = str(
        create_run_batch(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_kind="comparison",
            notes=None,
        )["batch"]["id"]
    )

    try:
        attach_run_batch_item(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
            run_id=run_id,
            candidate_label=None,
            strategy_profile_version_id=strategy_inactive,
            scoring_profile_version_id=None,
        )
        _test("inactive strategy version rejected", False, detail="should have raised")
    except RunBatchError as exc:
        _test("inactive strategy version rejected", exc.status_code == 400)

    try:
        attach_run_batch_item(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
            run_id=run_id,
            candidate_label=None,
            strategy_profile_version_id=None,
            scoring_profile_version_id=str(scoring_inactive),
        )
        _test("inactive scoring version rejected", False, detail="should have raised")
    except RunBatchError as exc:
        _test("inactive scoring version rejected", exc.status_code == 400)


def test_no_orchestrator_evaluation_ranking_side_effect() -> None:
    print("\n=== 7. No orchestrator/evaluation/ranking side effect ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    run_id = _seed_run(sb, project_id, OWNER_A)
    strategy_id = _seed_strategy_version(sb, OWNER_A)
    scoring_id = _seed_scoring_version(sb, OWNER_A)

    batch_id = str(
        create_run_batch(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_kind="comparison",
            notes="smoke",
        )["batch"]["id"]
    )
    attach_run_batch_item(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        run_id=run_id,
        candidate_label="baseline",
        strategy_profile_version_id=strategy_id,
        scoring_profile_version_id=str(scoring_id),
    )

    forbidden_tables = [
        "app.run_evaluations",
        "app.run_ranking_results",
        "app.project_selected_runs",
        "app.nesting_run_snapshots",
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.run_manufacturing_metrics",
    ]
    for table_name in forbidden_tables:
        writes = [entry for entry in sb.write_log if entry.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    import api.services.run_batches as svc_mod

    source = Path(svc_mod.__file__).read_text(encoding="utf-8")
    _test("no run_creation in service", "create_queued_run" not in source)
    _test("no run_evaluations in service", "run_evaluations" not in source)
    _test("no run_ranking_results in service", "run_ranking_results" not in source)
    _test("no orchestrator wording in service", "orchestrator" not in source)


def test_migration_structure() -> None:
    print("\n=== 8. Migration structure ===")
    migration_path = ROOT / "supabase" / "migrations" / "20260324130000_h3_e2_t1_run_batch_modell.sql"
    sql = migration_path.read_text(encoding="utf-8")

    _test("creates run_batches", "create table if not exists app.run_batches" in sql)
    _test("creates run_batch_items", "create table if not exists app.run_batch_items" in sql)
    _test("batch item PK(batch_id, run_id)", "primary key (batch_id, run_id)" in sql)
    _test("candidate_label exists", "candidate_label text" in sql)
    _test("strategy ref exists", "strategy_profile_version_id uuid references app.run_strategy_profile_versions(id)" in sql)
    _test("scoring ref exists", "scoring_profile_version_id uuid references app.scoring_profile_versions(id)" in sql)
    _test("RLS enabled run_batches", "alter table app.run_batches enable row level security" in sql)
    _test("RLS enabled run_batch_items", "alter table app.run_batch_items enable row level security" in sql)

    ddl_lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    ddl_only = "\n".join(ddl_lines)
    _test("no run_evaluations in migration", "run_evaluations" not in ddl_only)
    _test("no run_ranking_results in migration", "run_ranking_results" not in ddl_only)
    _test("no project_selected_runs in migration", "project_selected_runs" not in ddl_only)


def test_route_structure() -> None:
    print("\n=== 9. Route structure ===")
    import api.routes.run_batches as route_mod
    from api.routes.run_batches import router

    route_source = Path(route_mod.__file__).read_text(encoding="utf-8")
    _test("route prefix", router.prefix == "/projects/{project_id}/run-batches")
    _test("no run_evaluations in route", "run_evaluations" not in route_source)
    _test("no run_ranking_results in route", "run_ranking_results" not in route_source)

    route_paths = sorted({route.path for route in router.routes})
    _test("has base route", "/projects/{project_id}/run-batches" in route_paths)
    _test("has batch-id route", "/projects/{project_id}/run-batches/{batch_id}" in route_paths)
    _test("has batch-items route", "/projects/{project_id}/run-batches/{batch_id}/items" in route_paths)
    _test("has batch-item delete route", "/projects/{project_id}/run-batches/{batch_id}/items/{run_id}" in route_paths)


if __name__ == "__main__":
    print("H3-E2-T1 smoke: run batch model\n")

    test_batch_crud()
    test_attach_list_remove_item()
    test_duplicate_item_rejected()
    test_foreign_project_run_rejected()
    test_foreign_owner_versions_rejected()
    test_inactive_versions_rejected()
    test_no_orchestrator_evaluation_ranking_side_effect()
    test_migration_structure()
    test_route_structure()

    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        raise SystemExit(1)

    print("SMOKE PASS")
    raise SystemExit(0)
