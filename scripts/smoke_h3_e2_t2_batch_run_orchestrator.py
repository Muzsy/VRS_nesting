#!/usr/bin/env python3
"""H3-E2-T2 smoke: batch run orchestrator service."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_batch_orchestrator import (  # noqa: E402
    RunBatchOrchestratorError,
    orchestrate_run_batch_candidates,
)
from api.services.run_creation import RunCreationError  # noqa: E402
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
        token = str(raw_filter or "").strip()
        text = "" if value is None else str(value)
        if token.startswith("eq."):
            return text == token[3:]
        if token.startswith("neq."):
            return text != token[4:]
        return True

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        rows = [dict(row) for row in self.tables.get(table, [])]
        meta_keys = {"select", "order", "limit", "offset"}
        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            rows = [row for row in rows if self._match_filter(row.get(key), raw_filter)]

        order_clause = str(params.get("order") or "").strip()
        if order_clause:
            for token in reversed([part.strip() for part in order_clause.split(",") if part.strip()]):
                col = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda row, column=col: str(row.get(column) or ""), reverse=reverse)

        limit_raw = str(params.get("limit") or "").strip()
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)
        if table == "app.run_batches":
            row.setdefault("id", str(uuid4()))
        if table == "app.nesting_runs":
            row.setdefault("id", str(uuid4()))
        if table == "app.run_batch_items":
            batch_id = str(row.get("batch_id") or "").strip()
            run_id = str(row.get("run_id") or "").strip()
            for existing in self.tables["app.run_batch_items"]:
                if (
                    str(existing.get("batch_id") or "").strip() == batch_id
                    and str(existing.get("run_id") or "").strip() == run_id
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint run_batch_items_pkey")

        self.tables.setdefault(table, []).append(row)
        self.write_log.append({"op": "insert", "table": table, "payload": dict(row)})
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
        updated: list[dict[str, Any]] = []
        for row in self.tables.get(table, []):
            ok = True
            for key, raw_filter in filters.items():
                if not self._match_filter(row.get(key), raw_filter):
                    ok = False
                    break
            if ok:
                row.update(payload)
                updated.append(dict(row))
        self.write_log.append({"op": "update", "table": table, "payload": dict(payload), "filters": dict(filters)})
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        remaining: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        for row in self.tables.get(table, []):
            ok = True
            for key, raw_filter in filters.items():
                if not self._match_filter(row.get(key), raw_filter):
                    ok = False
                    break
            if ok:
                removed.append(dict(row))
            else:
                remaining.append(row)
        self.tables[table] = remaining
        self.write_log.append({"op": "delete", "table": table, "filters": dict(filters)})

        if table == "app.run_batches" and removed:
            removed_batch_ids = {str(row.get("id") or "").strip() for row in removed}
            self.tables["app.run_batch_items"] = [
                row
                for row in self.tables["app.run_batch_items"]
                if str(row.get("batch_id") or "").strip() not in removed_batch_ids
            ]


OWNER_A = str(uuid4())
OWNER_B = str(uuid4())
TOKEN = "fake-token"


def _seed_project(sb: FakeSupabaseClient, owner: str) -> str:
    project_id = str(uuid4())
    sb.tables["app.projects"].append(
        {
            "id": project_id,
            "owner_user_id": owner,
            "lifecycle": "active",
        }
    )
    return project_id


def _seed_strategy_version(sb: FakeSupabaseClient, owner: str, *, is_active: bool = True) -> str:
    version_id = str(uuid4())
    sb.tables["app.run_strategy_profile_versions"].append(
        {
            "id": version_id,
            "run_strategy_profile_id": str(uuid4()),
            "owner_user_id": owner,
            "version_no": 1,
            "lifecycle": "draft",
            "is_active": is_active,
        }
    )
    return version_id


def _seed_scoring_version(sb: FakeSupabaseClient, owner: str, *, is_active: bool = True) -> str:
    version_id = str(uuid4())
    sb.tables["app.scoring_profile_versions"].append(
        {
            "id": version_id,
            "scoring_profile_id": str(uuid4()),
            "owner_user_id": owner,
            "version_no": 1,
            "lifecycle": "draft",
            "is_active": is_active,
        }
    )
    return version_id


def _patch_run_creator(fake_creator: Any) -> Any:
    import api.services.run_batch_orchestrator as orchestrator_module

    original = orchestrator_module.create_queued_run_from_project_snapshot
    orchestrator_module.create_queued_run_from_project_snapshot = fake_creator
    return original


def _restore_run_creator(original_creator: Any) -> None:
    import api.services.run_batch_orchestrator as orchestrator_module

    orchestrator_module.create_queued_run_from_project_snapshot = original_creator


def test_multi_candidate_success() -> None:
    print("\n=== 1. Multi-candidate orchestrator success ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    strategy_1 = _seed_strategy_version(sb, OWNER_A)
    scoring_1 = _seed_scoring_version(sb, OWNER_A)
    strategy_2 = _seed_strategy_version(sb, OWNER_A)
    scoring_2 = _seed_scoring_version(sb, OWNER_A)

    calls: list[dict[str, Any]] = []

    def fake_creator(**kwargs: Any) -> dict[str, Any]:
        run_row = sb.insert_row(
            table="app.nesting_runs",
            access_token=TOKEN,
            payload={
                "project_id": kwargs["project_id"],
                "requested_by": kwargs["owner_user_id"],
                "status": "queued",
                "run_purpose": kwargs.get("run_purpose"),
                "idempotency_key": kwargs.get("idempotency_key"),
            },
        )
        calls.append(dict(kwargs))
        return {
            "run": run_row,
            "snapshot": {"id": str(uuid4())},
            "queue": {"id": str(uuid4()), "queue_state": "pending"},
            "was_deduplicated": False,
            "dedup_reason": None,
        }

    original_creator = _patch_run_creator(fake_creator)
    try:
        result = orchestrate_run_batch_candidates(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=None,
            batch_kind="comparison",
            notes="batch orchestration smoke",
            candidates=[
                {
                    "candidate_label": "baseline",
                    "strategy_profile_version_id": strategy_1,
                    "scoring_profile_version_id": scoring_1,
                    "run_purpose": "nesting",
                    "idempotency_key": "cand-1",
                },
                {
                    "candidate_label": "aggressive",
                    "strategy_profile_version_id": strategy_2,
                    "scoring_profile_version_id": scoring_2,
                    "run_purpose": "nesting",
                    "idempotency_key": "cand-2",
                },
            ],
        )
    finally:
        _restore_run_creator(original_creator)

    _test("batch created", bool(result.get("batch_was_created")))
    _test("two orchestrated candidates", int(result.get("total_candidates") or 0) == 2)
    _test("run creation called twice", len(calls) == 2)
    _test("two run rows created", len(sb.tables["app.nesting_runs"]) == 2)
    _test("two batch item rows created", len(sb.tables["app.run_batch_items"]) == 2)

    item_rows = result.get("items")
    _test("result items list type", isinstance(item_rows, list))
    if isinstance(item_rows, list) and len(item_rows) == 2:
        _test("candidate[0] label stored", str(item_rows[0].get("candidate_label") or "") == "baseline")
        _test(
            "candidate[1] strategy stored",
            str(item_rows[1].get("strategy_profile_version_id") or "") == strategy_2,
        )
        _test("run status queued", str(item_rows[0].get("run_status") or "") == "queued")


def test_foreign_owner_versions_rejected() -> None:
    print("\n=== 2. Foreign-owner strategy/scoring rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    strategy_foreign = _seed_strategy_version(sb, OWNER_B)
    scoring_own = _seed_scoring_version(sb, OWNER_A)

    calls: list[dict[str, Any]] = []

    def fake_creator(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        raise RuntimeError("run creator should not be called for foreign strategy")

    original_creator = _patch_run_creator(fake_creator)
    try:
        try:
            orchestrate_run_batch_candidates(
                supabase=sb,
                access_token=TOKEN,
                owner_user_id=OWNER_A,
                project_id=project_id,
                batch_id=None,
                batch_kind="comparison",
                notes=None,
                candidates=[
                    {
                        "candidate_label": "foreign-strategy",
                        "strategy_profile_version_id": strategy_foreign,
                        "scoring_profile_version_id": scoring_own,
                        "run_purpose": "nesting",
                        "idempotency_key": "cand-foreign",
                    }
                ],
            )
            _test("foreign strategy rejected", False, detail="should have raised")
        except RunBatchOrchestratorError as exc:
            _test("foreign strategy rejected", exc.status_code == 403)
            _test("error mentions candidate index", "candidate[0]" in exc.detail)
    finally:
        _restore_run_creator(original_creator)

    _test("run creator not called", len(calls) == 0)
    _test("no batch row created", len(sb.tables["app.run_batches"]) == 0)
    _test("no batch item row created", len(sb.tables["app.run_batch_items"]) == 0)
    _test("no run row created", len(sb.tables["app.nesting_runs"]) == 0)


def test_fail_fast_with_new_batch_rollback() -> None:
    print("\n=== 3. Fail-fast rollback (new batch) ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    strategy_1 = _seed_strategy_version(sb, OWNER_A)
    scoring_1 = _seed_scoring_version(sb, OWNER_A)
    strategy_2 = _seed_strategy_version(sb, OWNER_A)
    scoring_2 = _seed_scoring_version(sb, OWNER_A)

    call_no = 0

    def fake_creator(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_no
        if call_no == 1:
            call_no += 1
            raise RunCreationError(status_code=422, detail="snapshot builder failed")
        call_no += 1
        run_row = sb.insert_row(
            table="app.nesting_runs",
            access_token=TOKEN,
            payload={
                "project_id": kwargs["project_id"],
                "requested_by": kwargs["owner_user_id"],
                "status": "queued",
                "run_purpose": kwargs.get("run_purpose"),
            },
        )
        return {
            "run": run_row,
            "snapshot": {"id": str(uuid4())},
            "queue": {"id": str(uuid4())},
            "was_deduplicated": False,
            "dedup_reason": None,
        }

    original_creator = _patch_run_creator(fake_creator)
    try:
        try:
            orchestrate_run_batch_candidates(
                supabase=sb,
                access_token=TOKEN,
                owner_user_id=OWNER_A,
                project_id=project_id,
                batch_id=None,
                batch_kind="comparison",
                notes=None,
                candidates=[
                    {
                        "candidate_label": "ok-first",
                        "strategy_profile_version_id": strategy_1,
                        "scoring_profile_version_id": scoring_1,
                        "run_purpose": "nesting",
                        "idempotency_key": "ff-1",
                    },
                    {
                        "candidate_label": "failing-second",
                        "strategy_profile_version_id": strategy_2,
                        "scoring_profile_version_id": scoring_2,
                        "run_purpose": "nesting",
                        "idempotency_key": "ff-2",
                    },
                ],
            )
            _test("fail-fast raised", False, detail="should have raised")
        except RunBatchOrchestratorError as exc:
            _test("run creation failure propagated", exc.status_code == 422)
            _test("run creation detail kept", "run creation failed" in exc.detail)
    finally:
        _restore_run_creator(original_creator)

    _test("new batch removed on rollback", len(sb.tables["app.run_batches"]) == 0)
    _test("attached items removed on rollback", len(sb.tables["app.run_batch_items"]) == 0)
    _test("new runs removed on rollback", len(sb.tables["app.nesting_runs"]) == 0)


def test_fail_fast_with_existing_batch_rollback_items() -> None:
    print("\n=== 4. Fail-fast rollback (existing batch) ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    strategy_1 = _seed_strategy_version(sb, OWNER_A)
    scoring_1 = _seed_scoring_version(sb, OWNER_A)
    strategy_2 = _seed_strategy_version(sb, OWNER_A)
    scoring_2 = _seed_scoring_version(sb, OWNER_A)

    existing_batch = sb.insert_row(
        table="app.run_batches",
        access_token=TOKEN,
        payload={
            "project_id": project_id,
            "created_by": OWNER_A,
            "batch_kind": "comparison",
            "notes": "existing",
        },
    )
    existing_batch_id = str(existing_batch.get("id") or "")

    call_no = 0

    def fake_creator(**kwargs: Any) -> dict[str, Any]:
        nonlocal call_no
        if call_no == 1:
            call_no += 1
            raise RunCreationError(status_code=422, detail="second candidate failed")
        call_no += 1
        run_row = sb.insert_row(
            table="app.nesting_runs",
            access_token=TOKEN,
            payload={
                "project_id": kwargs["project_id"],
                "requested_by": kwargs["owner_user_id"],
                "status": "queued",
                "run_purpose": kwargs.get("run_purpose"),
            },
        )
        return {
            "run": run_row,
            "snapshot": {"id": str(uuid4())},
            "queue": {"id": str(uuid4())},
            "was_deduplicated": False,
            "dedup_reason": None,
        }

    original_creator = _patch_run_creator(fake_creator)
    try:
        try:
            orchestrate_run_batch_candidates(
                supabase=sb,
                access_token=TOKEN,
                owner_user_id=OWNER_A,
                project_id=project_id,
                batch_id=existing_batch_id,
                batch_kind="comparison",
                notes=None,
                candidates=[
                    {
                        "candidate_label": "first",
                        "strategy_profile_version_id": strategy_1,
                        "scoring_profile_version_id": scoring_1,
                        "run_purpose": "nesting",
                        "idempotency_key": "existing-1",
                    },
                    {
                        "candidate_label": "second",
                        "strategy_profile_version_id": strategy_2,
                        "scoring_profile_version_id": scoring_2,
                        "run_purpose": "nesting",
                        "idempotency_key": "existing-2",
                    },
                ],
            )
            _test("existing batch fail-fast raised", False, detail="should have raised")
        except RunBatchOrchestratorError as exc:
            _test("existing batch failure code", exc.status_code == 422)
    finally:
        _restore_run_creator(original_creator)

    _test("existing batch preserved", len(sb.tables["app.run_batches"]) == 1)
    _test("existing batch id unchanged", str(sb.tables["app.run_batches"][0].get("id") or "") == existing_batch_id)
    _test("temporary batch items rolled back", len(sb.tables["app.run_batch_items"]) == 0)
    _test("temporary runs rolled back", len(sb.tables["app.nesting_runs"]) == 0)


def test_no_evaluation_ranking_side_effect() -> None:
    print("\n=== 5. No evaluation/ranking side effects ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, OWNER_A)
    strategy_id = _seed_strategy_version(sb, OWNER_A)
    scoring_id = _seed_scoring_version(sb, OWNER_A)

    def fake_creator(**kwargs: Any) -> dict[str, Any]:
        run_row = sb.insert_row(
            table="app.nesting_runs",
            access_token=TOKEN,
            payload={
                "project_id": kwargs["project_id"],
                "requested_by": kwargs["owner_user_id"],
                "status": "queued",
                "run_purpose": kwargs.get("run_purpose"),
            },
        )
        return {
            "run": run_row,
            "snapshot": {"id": str(uuid4())},
            "queue": {"id": str(uuid4())},
            "was_deduplicated": False,
            "dedup_reason": None,
        }

    original_creator = _patch_run_creator(fake_creator)
    try:
        orchestrate_run_batch_candidates(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=None,
            batch_kind="comparison",
            notes=None,
            candidates=[
                {
                    "candidate_label": "side-effect-check",
                    "strategy_profile_version_id": strategy_id,
                    "scoring_profile_version_id": scoring_id,
                    "run_purpose": "nesting",
                    "idempotency_key": "side-1",
                }
            ],
        )
    finally:
        _restore_run_creator(original_creator)

    forbidden_tables = [
        "app.run_evaluations",
        "app.run_ranking_results",
        "app.project_selected_runs",
    ]
    for table_name in forbidden_tables:
        writes = [entry for entry in sb.write_log if entry.get("table") == table_name]
        _test(f"no write to {table_name}", len(writes) == 0)

    import api.services.run_batch_orchestrator as orchestrator_module

    source = Path(orchestrator_module.__file__).read_text(encoding="utf-8")
    _test("service reuses canonical run create", "create_queued_run_from_project_snapshot" in source)
    _test("service has no run_evaluations logic", "run_evaluations" not in source)
    _test("service has no run_ranking_results logic", "run_ranking_results" not in source)


def test_route_structure() -> None:
    print("\n=== 6. Route structure ===")
    import api.routes.run_batches as route_module
    from api.routes.run_batches import router

    source = Path(route_module.__file__).read_text(encoding="utf-8")
    route_paths = sorted({route.path for route in router.routes})
    _test(
        "orchestrate route exists",
        "/projects/{project_id}/run-batches/orchestrate" in route_paths,
    )
    _test("route has no evaluation keyword", "run_evaluations" not in source)
    _test("route has no ranking keyword", "run_ranking_results" not in source)


if __name__ == "__main__":
    print("H3-E2-T2 smoke: batch run orchestrator\n")

    test_multi_candidate_success()
    test_foreign_owner_versions_rejected()
    test_fail_fast_with_new_batch_rollback()
    test_fail_fast_with_existing_batch_rollback_items()
    test_no_evaluation_ranking_side_effect()
    test_route_structure()

    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        raise SystemExit(1)

    print("SMOKE PASS")
    raise SystemExit(0)
