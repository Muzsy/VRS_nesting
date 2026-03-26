#!/usr/bin/env python3
"""H3-E3-T3 smoke: best-by-objective read-side projections."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_best_by_objective import (  # noqa: E402
    RunBestByObjectiveError,
    list_best_by_objective,
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
            "app.run_batches": [],
            "app.run_batch_items": [],
            "app.run_ranking_results": [],
            "app.run_evaluations": [],
            "app.run_metrics": [],
            "app.run_manufacturing_metrics": [],
            "app.nesting_run_snapshots": [],
            "app.run_layout_unplaced": [],
            "app.project_selected_runs": [],
            "app.run_business_metrics": [],
        }
        self.write_log: list[dict[str, Any]] = []

    @staticmethod
    def _match_filter(value: Any, raw_filter: str) -> bool:
        token = str(raw_filter or "").strip()
        text = "" if value is None else str(value)
        if token.startswith("eq."):
            needle = token[3:]
            lower = needle.lower()
            if lower == "true":
                return bool(value) is True
            if lower == "false":
                return bool(value) is False
            return text == needle
        if token.startswith("neq."):
            return text != token[4:]
        return True

    @staticmethod
    def _order_value(row: dict[str, Any], column: str) -> Any:
        value = row.get(column)
        if value is None:
            return ""
        if isinstance(value, (int, float, str)):
            return value
        return str(value)

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
            parts = [part.strip() for part in order_clause.split(",") if part.strip()]
            for token in reversed(parts):
                column = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda row, col=column: self._order_value(row, col), reverse=reverse)

        limit_raw = str(params.get("limit") or "").strip()
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)
        if table in {"app.run_batches"}:
            row.setdefault("id", str(uuid4()))
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
            if all(self._match_filter(row.get(key), raw_filter) for key, raw_filter in filters.items()):
                row.update(payload)
                updated.append(dict(row))
        self.write_log.append({"op": "update", "table": table, "payload": dict(payload), "filters": dict(filters)})
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        remaining: list[dict[str, Any]] = []
        for row in self.tables.get(table, []):
            if all(self._match_filter(row.get(key), raw_filter) for key, raw_filter in filters.items()):
                continue
            remaining.append(row)
        self.tables[table] = remaining
        self.write_log.append({"op": "delete", "table": table, "filters": dict(filters)})


OWNER_A = str(uuid4())
OWNER_B = str(uuid4())
TOKEN = "fake-token"


def _seed_project(sb: FakeSupabaseClient, *, owner: str) -> str:
    project_id = str(uuid4())
    sb.tables["app.projects"].append(
        {
            "id": project_id,
            "owner_user_id": owner,
            "lifecycle": "active",
        }
    )
    return project_id


def _seed_batch(sb: FakeSupabaseClient, *, project_id: str, owner: str) -> str:
    row = {
        "id": str(uuid4()),
        "project_id": project_id,
        "created_by": owner,
        "batch_kind": "comparison",
        "notes": "best-by-objective smoke",
        "created_at": "2026-03-26T12:00:00Z",
    }
    sb.tables["app.run_batches"].append(row)
    return str(row["id"])


def _seed_batch_item(
    sb: FakeSupabaseClient,
    *,
    batch_id: str,
    run_id: str,
    candidate_label: str,
) -> None:
    sb.tables["app.run_batch_items"].append(
        {
            "batch_id": batch_id,
            "run_id": run_id,
            "candidate_label": candidate_label,
            "created_at": "2026-03-26T12:01:00Z",
        }
    )


def _seed_ranking(
    sb: FakeSupabaseClient,
    *,
    batch_id: str,
    run_id: str,
    rank_no: int,
) -> None:
    sb.tables["app.run_ranking_results"].append(
        {
            "batch_id": batch_id,
            "run_id": run_id,
            "rank_no": rank_no,
            "ranking_reason_jsonb": {
                "rank_no": rank_no,
                "note": "seed ranking",
            },
            "created_at": "2026-03-26T12:02:00Z",
        }
    )


def _seed_evaluation(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    total_score: float,
) -> None:
    sb.tables["app.run_evaluations"].append(
        {
            "run_id": run_id,
            "scoring_profile_version_id": str(uuid4()),
            "total_score": total_score,
            "evaluation_jsonb": {
                "components": {"seed": {"status": "applied"}},
                "input_metrics": {"seed_score_hint": total_score},
            },
            "created_at": "2026-03-26T12:03:00Z",
        }
    )


def _seed_run_metrics(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    utilization_ratio: float,
    used_sheet_count: int,
    unplaced_count: int,
    remnant_value: float,
) -> None:
    sb.tables["app.run_metrics"].append(
        {
            "run_id": run_id,
            "placed_count": 10,
            "unplaced_count": unplaced_count,
            "used_sheet_count": used_sheet_count,
            "utilization_ratio": utilization_ratio,
            "remnant_value": remnant_value,
            "metrics_jsonb": {},
            "created_at": "2026-03-26T12:04:00Z",
        }
    )


def _seed_manufacturing_metrics(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    estimated_process_time_s: float,
) -> None:
    sb.tables["app.run_manufacturing_metrics"].append(
        {
            "run_id": run_id,
            "estimated_process_time_s": estimated_process_time_s,
            "estimated_cut_length_mm": 1000.0,
            "estimated_rapid_length_mm": 200.0,
            "pierce_count": 5,
            "created_at": "2026-03-26T12:05:00Z",
        }
    )


def _seed_snapshot(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    parts_manifest: list[dict[str, Any]],
) -> None:
    sb.tables["app.nesting_run_snapshots"].append(
        {
            "run_id": run_id,
            "parts_manifest_jsonb": list(parts_manifest),
            "snapshot_hash_sha256": f"hash-{run_id}",
            "snapshot_version": "h2_e5_t2_snapshot_v1",
        }
    )


def _seed_unplaced(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    part_revision_id: str,
    remaining_qty: int,
) -> None:
    sb.tables["app.run_layout_unplaced"].append(
        {
            "run_id": run_id,
            "part_revision_id": part_revision_id,
            "remaining_qty": remaining_qty,
            "reason": "not-fitted",
            "created_at": "2026-03-26T12:06:00Z",
        }
    )


def _seed_objective_dataset(sb: FakeSupabaseClient, *, owner: str) -> tuple[str, str, dict[str, str]]:
    project_id = _seed_project(sb, owner=owner)
    batch_id = _seed_batch(sb, project_id=project_id, owner=owner)

    run_a = str(uuid4())
    run_b = str(uuid4())
    run_c = str(uuid4())

    _seed_batch_item(sb, batch_id=batch_id, run_id=run_a, candidate_label="alpha")
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_b, candidate_label="beta")
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_c, candidate_label="gamma")

    # Persisted ranking order intentionally differs from objective winners.
    _seed_ranking(sb, batch_id=batch_id, run_id=run_b, rank_no=1)
    _seed_ranking(sb, batch_id=batch_id, run_id=run_c, rank_no=2)
    _seed_ranking(sb, batch_id=batch_id, run_id=run_a, rank_no=3)

    _seed_evaluation(sb, run_id=run_a, total_score=0.74)
    _seed_evaluation(sb, run_id=run_b, total_score=0.81)
    _seed_evaluation(sb, run_id=run_c, total_score=0.79)

    _seed_run_metrics(
        sb,
        run_id=run_a,
        utilization_ratio=0.93,
        used_sheet_count=2,
        unplaced_count=0,
        remnant_value=12.0,
    )
    _seed_run_metrics(
        sb,
        run_id=run_b,
        utilization_ratio=0.86,
        used_sheet_count=2,
        unplaced_count=1,
        remnant_value=15.0,
    )
    _seed_run_metrics(
        sb,
        run_id=run_c,
        utilization_ratio=0.84,
        used_sheet_count=3,
        unplaced_count=2,
        remnant_value=9.0,
    )

    _seed_manufacturing_metrics(sb, run_id=run_a, estimated_process_time_s=52.0)
    _seed_manufacturing_metrics(sb, run_id=run_b, estimated_process_time_s=61.0)
    _seed_manufacturing_metrics(sb, run_id=run_c, estimated_process_time_s=45.0)

    part_high = str(uuid4())
    part_low = str(uuid4())
    parts_manifest = [
        {
            "part_revision_id": part_high,
            "required_qty": 10,
            "placement_priority": 5,
        },
        {
            "part_revision_id": part_low,
            "required_qty": 8,
            "placement_priority": 70,
        },
    ]
    _seed_snapshot(sb, run_id=run_a, parts_manifest=parts_manifest)
    _seed_snapshot(sb, run_id=run_b, parts_manifest=parts_manifest)
    _seed_snapshot(sb, run_id=run_c, parts_manifest=parts_manifest)

    _seed_unplaced(sb, run_id=run_b, part_revision_id=part_high, remaining_qty=3)
    _seed_unplaced(sb, run_id=run_c, part_revision_id=part_high, remaining_qty=1)
    _seed_unplaced(sb, run_id=run_c, part_revision_id=part_low, remaining_qty=2)

    return project_id, batch_id, {"a": run_a, "b": run_b, "c": run_c}


def _get_objective_item(result: dict[str, Any], objective: str) -> dict[str, Any]:
    rows = result.get("items")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict) and str(row.get("objective") or "") == objective:
            return row
    return {}


def test_material_best_success() -> None:
    print("\n=== 1. material-best returns expected winner ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, runs = _seed_objective_dataset(sb, owner=OWNER_A)
    result = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        objective="material-best",
    )
    item = _get_objective_item(result, "material-best")
    _test("status available", str(item.get("status") or "") == "available")
    _test("winner is run_a by utilization", str(item.get("run_id") or "") == runs["a"])


def test_time_best_success() -> None:
    print("\n=== 2. time-best returns expected winner ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, runs = _seed_objective_dataset(sb, owner=OWNER_A)
    result = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        objective="time-best",
    )
    item = _get_objective_item(result, "time-best")
    _test("status available", str(item.get("status") or "") == "available")
    _test("winner is run_c by process time", str(item.get("run_id") or "") == runs["c"])


def test_priority_best_success() -> None:
    print("\n=== 3. priority-best computed from snapshot + unplaced ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, runs = _seed_objective_dataset(sb, owner=OWNER_A)
    result = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        objective="priority-best",
    )
    item = _get_objective_item(result, "priority-best")
    reason = item.get("objective_reason_jsonb") if isinstance(item.get("objective_reason_jsonb"), dict) else {}
    _test("status available", str(item.get("status") or "") == "available")
    _test("winner is run_a by fulfilment", str(item.get("run_id") or "") == runs["a"])
    _test("reason contains formula snapshot", isinstance(((reason.get("metric_snapshot") or {}).get("formula")), dict))


def test_cost_best_unsupported() -> None:
    print("\n=== 4. cost-best explicit unsupported ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, _ = _seed_objective_dataset(sb, owner=OWNER_A)
    result = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
        objective="cost-best",
    )
    item = _get_objective_item(result, "cost-best")
    reason = item.get("objective_reason_jsonb") if isinstance(item.get("objective_reason_jsonb"), dict) else {}
    _test(
        "status unsupported_pending_business_metrics",
        str(item.get("status") or "") == "unsupported_pending_business_metrics",
    )
    _test("no winner run id", item.get("run_id") is None)
    _test("unsupported reason present", "unsupported_reason" in reason)


def test_no_ranking_no_fallback() -> None:
    print("\n=== 5. no ranking means no silent fallback ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    run_id = str(uuid4())
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_id, candidate_label="only-run")
    _seed_evaluation(sb, run_id=run_id, total_score=0.91)
    _seed_run_metrics(sb, run_id=run_id, utilization_ratio=0.9, used_sheet_count=1, unplaced_count=0, remnant_value=10.0)
    _seed_manufacturing_metrics(sb, run_id=run_id, estimated_process_time_s=44.0)
    _seed_snapshot(
        sb,
        run_id=run_id,
        parts_manifest=[
            {"part_revision_id": str(uuid4()), "required_qty": 3, "placement_priority": 10},
        ],
    )

    try:
        list_best_by_objective(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
            objective="material-best",
        )
        _test("missing ranking rejected", False, detail="should have raised")
    except RunBestByObjectiveError as exc:
        _test("missing ranking rejected", exc.status_code == 404)
        _test("error text references ranking", "ranking not found" in exc.detail)


def test_foreign_owner_forbidden() -> None:
    print("\n=== 6. foreign owner batch forbidden ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, _ = _seed_objective_dataset(sb, owner=OWNER_A)
    try:
        list_best_by_objective(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_B,
            project_id=project_id,
            batch_id=batch_id,
            objective="material-best",
        )
        _test("foreign owner rejected", False, detail="should have raised")
    except RunBestByObjectiveError as exc:
        _test("foreign owner rejected", exc.status_code == 404)


def test_read_only_no_side_effect_writes() -> None:
    print("\n=== 7. read-only route/service has no writes ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, _ = _seed_objective_dataset(sb, owner=OWNER_A)
    sb.write_log.clear()
    result = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    _test("returns four objectives", int(result.get("total") or 0) == 4)
    _test("no writes recorded", len(sb.write_log) == 0)
    forbidden_writes = {"app.run_evaluations", "app.run_ranking_results", "app.project_selected_runs", "app.run_business_metrics"}
    touched_tables = {str(entry.get("table") or "") for entry in sb.write_log}
    _test("no forbidden writes", not any(table in touched_tables for table in forbidden_writes))


def test_deterministic_projection() -> None:
    print("\n=== 8. deterministic projection on same input ===")
    sb = FakeSupabaseClient()
    project_id, batch_id, _ = _seed_objective_dataset(sb, owner=OWNER_A)
    first = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    second = list_best_by_objective(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    first_items = first.get("items") if isinstance(first.get("items"), list) else []
    second_items = second.get("items") if isinstance(second.get("items"), list) else []
    _test("same objective count", len(first_items) == len(second_items))
    _test("same payload across repeated calls", first_items == second_items)


if __name__ == "__main__":
    print("H3-E3-T3 smoke: best-by-objective read-side projections\n")

    test_material_best_success()
    test_time_best_success()
    test_priority_best_success()
    test_cost_best_unsupported()
    test_no_ranking_no_fallback()
    test_foreign_owner_forbidden()
    test_read_only_no_side_effect_writes()
    test_deterministic_projection()

    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        raise SystemExit(1)

    print("SMOKE PASS")
    raise SystemExit(0)
