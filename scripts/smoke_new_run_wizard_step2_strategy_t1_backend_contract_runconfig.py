#!/usr/bin/env python3
"""Smoke: New Run Wizard Step2 Strategy T1 backend contract + run_config wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.auth import AuthenticatedUser  # noqa: E402
from api.routes.run_configs import RunConfigCreateRequest, create_run_config  # noqa: E402
from api.routes.runs import RunCreateRequest  # noqa: E402
from api.services import run_creation as run_creation_module  # noqa: E402
from api.services.project_strategy_scoring_selection import _load_strategy_version_for_owner  # noqa: E402
from api.services.run_creation import RunCreationError, create_queued_run_from_project_snapshot  # noqa: E402
from api.services.run_snapshot_builder import build_run_snapshot_payload  # noqa: E402
from scripts.smoke_h1_e4_t1_run_snapshot_builder_h1_minimum import (  # noqa: E402
    FakeSupabaseClient as SnapshotBuilderFakeSupabaseClient,
    _seed_happy_path,
)

passed = 0
failed = 0

MIGRATION_PATH = ROOT / "supabase" / "migrations" / "20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql"


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


def _expect_http_error(fn: Any, *, status_code: int, detail_contains: str) -> HTTPException:
    try:
        fn()
    except HTTPException as exc:
        if exc.status_code != status_code:
            raise RuntimeError(f"unexpected HTTP status: {exc.status_code} != {status_code}")
        detail_text = str(exc.detail)
        if detail_contains not in detail_text:
            raise RuntimeError(f"unexpected HTTP detail: {detail_text!r}")
        return exc
    raise RuntimeError("expected HTTPException")


def _expect_run_creation_error(fn: Any, *, status_code: int, detail_contains: str) -> RunCreationError:
    try:
        fn()
    except RunCreationError as exc:
        if exc.status_code != status_code:
            raise RuntimeError(f"unexpected RunCreationError status: {exc.status_code} != {status_code}")
        if detail_contains not in exc.detail:
            raise RuntimeError(f"unexpected RunCreationError detail: {exc.detail!r}")
        return exc
    raise RuntimeError("expected RunCreationError")


def _as_bool_token(token: str) -> bool | None:
    lowered = token.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def _match_filter(value: Any, raw_filter: str) -> bool:
    token = raw_filter.strip()
    text = "" if value is None else str(value)

    if token.startswith("eq."):
        rhs = token[3:]
        rhs_bool = _as_bool_token(rhs)
        if rhs_bool is not None:
            return bool(value) is rhs_bool
        return text == rhs
    if token.startswith("neq."):
        rhs = token[4:]
        rhs_bool = _as_bool_token(rhs)
        if rhs_bool is not None:
            return bool(value) is not rhs_bool
        return text != rhs
    if token.startswith("in.(") and token.endswith(")"):
        members = [item.strip() for item in token[4:-1].split(",") if item.strip()]
        return text in members
    if token.startswith("gt."):
        try:
            return float(value) > float(token[3:])
        except (TypeError, ValueError):
            return False
    return True


def _apply_order(rows: list[dict[str, Any]], order_clause: str) -> list[dict[str, Any]]:
    ordered = list(rows)
    for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
        key = token.split(".")[0]
        reverse = ".desc" in token
        ordered.sort(key=lambda row: str(row.get(key) or ""), reverse=reverse)
    return ordered


class FakeRunConfigSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.projects": [],
            "app.file_objects": [],
            "app.run_strategy_profile_versions": [],
            "app.run_configs": [],
        }
        self.write_log: list[dict[str, Any]] = []

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        _ = access_token
        rows = [dict(item) for item in self.tables.get(table, [])]
        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if _match_filter(row.get(key), raw_filter)]

        order_clause = str(params.get("order") or "").strip()
        if order_clause:
            rows = _apply_order(rows, order_clause)

        offset = int(params.get("offset", "0") or "0")
        limit_raw = params.get("limit")
        if limit_raw:
            limit = int(limit_raw)
            rows = rows[offset : offset + limit]
        else:
            rows = rows[offset:]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)
        if "id" not in row:
            row["id"] = str(uuid4())
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self.tables.setdefault(table, []).append(dict(row))
        self.write_log.append({"op": "insert", "table": table, "payload": dict(row)})
        return row


class FakeRunCreationSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.projects": [],
            "app.run_configs": [],
            "app.nesting_runs": [],
            "app.nesting_run_snapshots": [],
            "app.run_queue": [],
        }

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        _ = access_token
        rows = [dict(item) for item in self.tables.get(table, [])]
        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if _match_filter(row.get(key), raw_filter)]
        order_clause = str(params.get("order") or "").strip()
        if order_clause:
            rows = _apply_order(rows, order_clause)
        limit_raw = params.get("limit")
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)
        now = datetime.now(timezone.utc).isoformat()
        if table == "app.nesting_runs":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.tables[table].append(dict(row))
            return row
        if table == "app.nesting_run_snapshots":
            row.setdefault("id", str(uuid4()))
            row.setdefault("created_at", now)
            self.tables[table].append(dict(row))
            return row
        if table == "app.run_queue":
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self.tables[table].append(dict(row))
            return row
        raise RuntimeError(f"unsupported insert table: {table}")

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        if table != "app.nesting_runs":
            return
        rows = self.tables[table]
        kept: list[dict[str, Any]] = []
        for row in rows:
            if all(_match_filter(row.get(key), raw_filter) for key, raw_filter in filters.items()):
                continue
            kept.append(row)
        self.tables[table] = kept


class StrategySelectCaptureFake:
    def __init__(self, *, version_id: str, owner_user_id: str) -> None:
        self.version_id = version_id
        self.owner_user_id = owner_user_id
        self.last_select: str = ""
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.run_strategy_profile_versions": [
                {
                    "id": version_id,
                    "run_strategy_profile_id": str(uuid4()),
                    "owner_user_id": owner_user_id,
                    "version_no": 1,
                    "lifecycle": "approved",
                    "is_active": True,
                    "solver_config_jsonb": {"quality_profile": "quality_default"},
                    "placement_config_jsonb": {"mode": "default"},
                    "manufacturing_bias_jsonb": {"priority": "balanced"},
                }
            ]
        }

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        _ = access_token
        self.last_select = str(params.get("select") or "")
        rows = [dict(item) for item in self.tables.get(table, [])]
        for key, raw_filter in params.items():
            if key in {"select", "limit", "order", "offset"}:
                continue
            rows = [row for row in rows if _match_filter(row.get(key), raw_filter)]
        limit_raw = params.get("limit")
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows


def _seed_run_config_route_happy_path(fake: FakeRunConfigSupabaseClient, *, owner_id: str) -> dict[str, str]:
    project_id = str(uuid4())
    stock_file_id = str(uuid4())
    part_file_id = str(uuid4())
    strategy_version_id = str(uuid4())
    fake.tables["app.projects"].append({"id": project_id, "owner_user_id": owner_id, "lifecycle": "active"})
    fake.tables["app.file_objects"].append({"id": stock_file_id, "project_id": project_id})
    fake.tables["app.file_objects"].append({"id": part_file_id, "project_id": project_id})
    fake.tables["app.run_strategy_profile_versions"].append(
        {
            "id": strategy_version_id,
            "owner_user_id": owner_id,
            "is_active": True,
        }
    )
    return {
        "project_id": project_id,
        "stock_file_id": stock_file_id,
        "part_file_id": part_file_id,
        "strategy_version_id": strategy_version_id,
    }


def test_migration_file() -> None:
    print("\n=== 1. Migration file assertions ===")
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    _test("migration file exists", MIGRATION_PATH.exists())
    _test("adds run_strategy_profile_version_id", "add column if not exists run_strategy_profile_version_id uuid" in sql)
    _test("adds solver_config_overrides_jsonb", "add column if not exists solver_config_overrides_jsonb jsonb" in sql)
    _test("adds strategy version index", "idx_run_configs_run_strategy_profile_version_id" in sql)
    _test("updates public.run_configs bridge", "create or replace view public.run_configs as" in sql)
    _test("updates run_configs_view_iud bridge", "create or replace function public.run_configs_view_iud()" in sql)


def test_run_config_route_contract_and_validation() -> None:
    print("\n=== 2. run_configs route contract + validation ===")
    owner_id = "00000000-0000-0000-0000-000000000001"
    user = AuthenticatedUser(id=owner_id, access_token="token-owner")

    fake = FakeRunConfigSupabaseClient()
    seeded = _seed_run_config_route_happy_path(fake, owner_id=owner_id)
    req = RunConfigCreateRequest(
        name="Strategy Config",
        stock_file_id=UUID(seeded["stock_file_id"]),
        parts_config=[
            {
                "file_id": UUID(seeded["part_file_id"]),
                "quantity": 3,
                "allowed_rotations_deg": [0, 90],
            }
        ],
        run_strategy_profile_version_id=UUID(seeded["strategy_version_id"]),
        solver_config_overrides_jsonb={
            "quality_profile": "quality_aggressive",
            "sa_eval_budget_sec": 15,
            "nesting_engine_runtime_policy": {
                "placer": "blf",
                "search": "none",
                "part_in_part": "off",
                "compaction": "off",
            },
            "engine_backend_hint": "sparrow_v1",
        },
    )
    result = create_run_config(
        project_id=UUID(seeded["project_id"]),
        req=req,
        user=user,
        supabase=fake,
    )
    _test("response includes strategy version", result.run_strategy_profile_version_id == seeded["strategy_version_id"])
    _test("response includes normalized quality profile", result.solver_config_overrides_jsonb.get("quality_profile") == "quality_aggressive")
    _test("response includes backend hint override", result.solver_config_overrides_jsonb.get("engine_backend_hint") == "sparrow_v1")
    _test("response includes runtime policy override", isinstance(result.solver_config_overrides_jsonb.get("nesting_engine_runtime_policy"), dict))

    insert_payload = fake.write_log[-1]["payload"]
    _test("insert payload stores strategy version", insert_payload.get("run_strategy_profile_version_id") == seeded["strategy_version_id"])
    _test("insert payload stores override json", isinstance(insert_payload.get("solver_config_overrides_jsonb"), dict))

    bad_key_req = RunConfigCreateRequest(
        stock_file_id=UUID(seeded["stock_file_id"]),
        parts_config=[{"file_id": UUID(seeded["part_file_id"])}],
        solver_config_overrides_jsonb={"unknown_key": "x"},
    )
    _expect_http_error(
        lambda: create_run_config(project_id=UUID(seeded["project_id"]), req=bad_key_req, user=user, supabase=fake),
        status_code=400,
        detail_contains="unsupported solver override key",
    )
    _test("invalid override key -> HTTP 400", True)

    bad_backend_req = RunConfigCreateRequest(
        stock_file_id=UUID(seeded["stock_file_id"]),
        parts_config=[{"file_id": UUID(seeded["part_file_id"])}],
        solver_config_overrides_jsonb={"engine_backend_hint": "auto"},
    )
    _expect_http_error(
        lambda: create_run_config(project_id=UUID(seeded["project_id"]), req=bad_backend_req, user=user, supabase=fake),
        status_code=400,
        detail_contains="invalid solver override engine_backend_hint",
    )
    _test("invalid backend hint -> HTTP 400", True)

    foreign_strategy_id = str(uuid4())
    fake.tables["app.run_strategy_profile_versions"].append(
        {
            "id": foreign_strategy_id,
            "owner_user_id": "00000000-0000-0000-0000-000000000099",
            "is_active": True,
        }
    )
    foreign_req = RunConfigCreateRequest(
        stock_file_id=UUID(seeded["stock_file_id"]),
        parts_config=[{"file_id": UUID(seeded["part_file_id"])}],
        run_strategy_profile_version_id=UUID(foreign_strategy_id),
    )
    _expect_http_error(
        lambda: create_run_config(project_id=UUID(seeded["project_id"]), req=foreign_req, user=user, supabase=fake),
        status_code=403,
        detail_contains="does not belong to owner",
    )
    _test("foreign-owner strategy version rejected", True)

    inactive_strategy_id = str(uuid4())
    fake.tables["app.run_strategy_profile_versions"].append(
        {
            "id": inactive_strategy_id,
            "owner_user_id": owner_id,
            "is_active": False,
        }
    )
    inactive_req = RunConfigCreateRequest(
        stock_file_id=UUID(seeded["stock_file_id"]),
        parts_config=[{"file_id": UUID(seeded["part_file_id"])}],
        run_strategy_profile_version_id=UUID(inactive_strategy_id),
    )
    _expect_http_error(
        lambda: create_run_config(project_id=UUID(seeded["project_id"]), req=inactive_req, user=user, supabase=fake),
        status_code=400,
        detail_contains="inactive",
    )
    _test("inactive strategy version rejected", True)


def test_run_create_request_model_and_run_creation_persistence() -> None:
    print("\n=== 3. run create request contract + run_creation run_config_id wiring ===")
    run_req = RunCreateRequest(
        run_config_id=uuid4(),
        run_strategy_profile_version_id=uuid4(),
        quality_profile="quality_default",
        engine_backend_hint="nesting_engine_v2",
        nesting_engine_runtime_policy={
            "placer": "nfp",
            "search": "sa",
            "part_in_part": "auto",
            "compaction": "slide",
            "sa_iters": 32,
        },
        sa_eval_budget_sec=9,
    )
    _test("RunCreateRequest accepts run_config_id", run_req.run_config_id is not None)
    _test("RunCreateRequest accepts run_strategy_profile_version_id", run_req.run_strategy_profile_version_id is not None)
    _test("RunCreateRequest accepts quality_profile", run_req.quality_profile == "quality_default")
    _test("RunCreateRequest accepts engine_backend_hint", run_req.engine_backend_hint == "nesting_engine_v2")
    _test("RunCreateRequest accepts runtime policy dict", isinstance(run_req.nesting_engine_runtime_policy, dict))

    fake = FakeRunCreationSupabaseClient()
    owner_id = "00000000-0000-0000-0000-000000000001"
    project_id = str(uuid4())
    run_config_id = str(uuid4())
    foreign_run_config_id = str(uuid4())
    other_project_run_config_id = str(uuid4())
    fake.tables["app.projects"].append({"id": project_id, "owner_user_id": owner_id, "lifecycle": "active"})
    fake.tables["app.run_configs"].append({"id": run_config_id, "project_id": project_id, "created_by": owner_id})
    fake.tables["app.run_configs"].append(
        {"id": foreign_run_config_id, "project_id": project_id, "created_by": "00000000-0000-0000-0000-000000000099"}
    )
    fake.tables["app.run_configs"].append(
        {"id": other_project_run_config_id, "project_id": str(uuid4()), "created_by": owner_id}
    )

    original_builder = run_creation_module.build_run_snapshot_payload

    def fake_builder(**kwargs: Any) -> dict[str, Any]:
        _ = kwargs
        return {
            "snapshot_version": "smoke.v1",
            "snapshot_hash_sha256": "a" * 64,
            "project_manifest_jsonb": {"project_id": project_id},
            "technology_manifest_jsonb": {"technology_setup_id": "tech-1"},
            "parts_manifest_jsonb": [{"part_revision_id": "part-1"}],
            "sheets_manifest_jsonb": [{"sheet_revision_id": "sheet-1"}],
            "geometry_manifest_jsonb": [{"geometry_revision_id": "geo-1"}],
            "solver_config_jsonb": {"quality_profile": "quality_default"},
            "manufacturing_manifest_jsonb": {"mode": "none"},
        }

    run_creation_module.build_run_snapshot_payload = fake_builder
    try:
        created = create_queued_run_from_project_snapshot(
            supabase=fake,
            access_token="token-owner",
            owner_user_id=owner_id,
            project_id=project_id,
            run_purpose="nesting",
            idempotency_key="idem-a",
            run_config_id=run_config_id,
            run_strategy_profile_version_id=str(uuid4()),
            quality_profile="quality_aggressive",
            engine_backend_hint="sparrow_v1",
            nesting_engine_runtime_policy={
                "placer": "blf",
                "search": "none",
                "part_in_part": "off",
                "compaction": "off",
            },
            sa_eval_budget_sec=17,
        )
        run_row = created["run"]
        _test("run row persists run_config_id", run_row.get("run_config_id") == run_config_id)
        request_payload = run_row.get("request_payload_jsonb")
        _test("request_payload includes source", isinstance(request_payload, dict) and "source" in request_payload)
        _test("request_payload includes snapshot hash", request_payload.get("snapshot_hash_sha256") == "a" * 64)
        _test("request_payload includes run_config_id", request_payload.get("run_config_id") == run_config_id)
        _test("request_payload includes strategy version field", "run_strategy_profile_version_id" in request_payload)
        _test("request_payload includes quality_profile", request_payload.get("quality_profile") == "quality_aggressive")
        _test("request_payload includes engine_backend_hint", request_payload.get("engine_backend_hint") == "sparrow_v1")
        _test("request_payload includes runtime policy presence flag", request_payload.get("has_nesting_engine_runtime_policy") is True)
        _test("request_payload includes sa_eval_budget_sec", request_payload.get("sa_eval_budget_sec") == 17)

        _expect_run_creation_error(
            lambda: create_queued_run_from_project_snapshot(
                supabase=fake,
                access_token="token-owner",
                owner_user_id=owner_id,
                project_id=project_id,
                run_config_id=foreign_run_config_id,
            ),
            status_code=403,
            detail_contains="does not belong to owner",
        )
        _test("run_creation rejects foreign-owner run_config", True)

        _expect_run_creation_error(
            lambda: create_queued_run_from_project_snapshot(
                supabase=fake,
                access_token="token-owner",
                owner_user_id=owner_id,
                project_id=project_id,
                run_config_id=other_project_run_config_id,
            ),
            status_code=400,
            detail_contains="does not belong to project",
        )
        _test("run_creation rejects foreign-project run_config", True)
    finally:
        run_creation_module.build_run_snapshot_payload = original_builder


def test_snapshot_builder_explicit_override_truth() -> None:
    print("\n=== 4. snapshot builder explicit override truth ===")
    fake = SnapshotBuilderFakeSupabaseClient()
    seeded = _seed_happy_path(fake)
    payload = build_run_snapshot_payload(
        supabase=fake,
        access_token="token-u1",
        owner_user_id=seeded["owner_id"],
        project_id=seeded["project_id"],
        quality_profile="fast_preview",
        engine_backend_hint="sparrow_v1",
        nesting_engine_runtime_policy={
            "placer": "blf",
            "search": "none",
            "part_in_part": "off",
            "compaction": "off",
        },
        sa_eval_budget_sec=23,
    )
    solver_cfg = payload.get("solver_config_jsonb")
    _test("solver_config_jsonb present", isinstance(solver_cfg, dict))
    _test("explicit quality_profile truth", isinstance(solver_cfg, dict) and solver_cfg.get("quality_profile") == "fast_preview")
    _test("explicit engine_backend_hint truth", isinstance(solver_cfg, dict) and solver_cfg.get("engine_backend_hint") == "sparrow_v1")
    runtime_policy = solver_cfg.get("nesting_engine_runtime_policy") if isinstance(solver_cfg, dict) else None
    _test("explicit runtime policy truth", isinstance(runtime_policy, dict) and runtime_policy.get("placer") == "blf")
    _test("sa_eval_budget_sec reflected in runtime policy", isinstance(runtime_policy, dict) and runtime_policy.get("sa_eval_budget_sec") == 23)


def test_strategy_loader_select_payload_columns() -> None:
    print("\n=== 5. strategy loader select payload columns ===")
    owner_id = "00000000-0000-0000-0000-000000000001"
    version_id = str(uuid4())
    fake = StrategySelectCaptureFake(version_id=version_id, owner_user_id=owner_id)
    version = _load_strategy_version_for_owner(
        supabase=fake,  # type: ignore[arg-type]
        access_token="token-owner",
        version_id=version_id,
        owner_user_id=owner_id,
        require_active=True,
    )
    _test("strategy loader returns row", str(version.get("id")) == version_id)
    _test("select includes solver_config_jsonb", "solver_config_jsonb" in fake.last_select)
    _test("select includes placement_config_jsonb", "placement_config_jsonb" in fake.last_select)
    _test("select includes manufacturing_bias_jsonb", "manufacturing_bias_jsonb" in fake.last_select)


def main() -> int:
    test_migration_file()
    test_run_config_route_contract_and_validation()
    test_run_create_request_model_and_run_creation_persistence()
    test_snapshot_builder_explicit_override_truth()
    test_strategy_loader_select_payload_columns()

    print(f"\nSummary: passed={passed}, failed={failed}")
    if failed:
        return 1
    print("PASS: New Run Wizard Step2 Strategy T1 backend contract smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
