#!/usr/bin/env python3
"""H3-E3-T2 smoke: ranking engine service."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_rankings import (  # noqa: E402
    RunRankingError,
    create_or_replace_run_batch_ranking,
    delete_run_batch_ranking,
    list_run_batch_ranking,
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
            "app.nesting_runs": [],
            "app.run_evaluations": [],
            "app.scoring_profile_versions": [],
            "app.run_ranking_results": [],
            "app.project_selected_runs": [],
            "app.run_comparison_results": [],
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

        if table in {"app.run_batches", "app.scoring_profile_versions", "app.nesting_runs", "app.run_ranking_results"}:
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

        if table == "app.run_ranking_results":
            batch_id = str(row.get("batch_id") or "").strip()
            run_id = str(row.get("run_id") or "").strip()
            rank_no = int(row.get("rank_no") or 0)
            for existing in self.tables["app.run_ranking_results"]:
                if (
                    str(existing.get("batch_id") or "").strip() == batch_id
                    and str(existing.get("run_id") or "").strip() == run_id
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint uq_run_ranking_results_batch_run")
                if (
                    str(existing.get("batch_id") or "").strip() == batch_id
                    and int(existing.get("rank_no") or 0) == rank_no
                ):
                    raise SupabaseHTTPError("duplicate key value violates unique constraint uq_run_ranking_results_batch_rank")

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
    batch = sb.insert_row(
        table="app.run_batches",
        access_token=TOKEN,
        payload={
            "project_id": project_id,
            "created_by": owner,
            "batch_kind": "comparison",
            "notes": "ranking smoke",
            "created_at": "2026-03-26T10:00:00Z",
        },
    )
    return str(batch.get("id") or "")


def _seed_run(sb: FakeSupabaseClient, *, project_id: str) -> str:
    run = sb.insert_row(
        table="app.nesting_runs",
        access_token=TOKEN,
        payload={
            "project_id": project_id,
            "status": "done",
        },
    )
    return str(run.get("id") or "")


def _seed_scoring_version(
    sb: FakeSupabaseClient,
    *,
    owner: str,
    tie_breaker_jsonb: dict[str, Any] | None = None,
) -> str:
    row = sb.insert_row(
        table="app.scoring_profile_versions",
        access_token=TOKEN,
        payload={
            "owner_user_id": owner,
            "tie_breaker_jsonb": dict(tie_breaker_jsonb or {}),
        },
    )
    return str(row.get("id") or "")


def _seed_batch_item(
    sb: FakeSupabaseClient,
    *,
    batch_id: str,
    run_id: str,
    candidate_label: str,
    scoring_profile_version_id: str | None,
) -> None:
    sb.insert_row(
        table="app.run_batch_items",
        access_token=TOKEN,
        payload={
            "batch_id": batch_id,
            "run_id": run_id,
            "candidate_label": candidate_label,
            "strategy_profile_version_id": None,
            "scoring_profile_version_id": scoring_profile_version_id,
            "created_at": "2026-03-26T10:01:00Z",
        },
    )


def _seed_evaluation(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    scoring_profile_version_id: str | None,
    total_score: float,
    utilization_ratio: float,
    unplaced_ratio: float,
    used_sheet_count: float,
    estimated_process_time_s: float | None,
) -> None:
    tie_breaker_inputs = {
        "primary": {
            "metric_key": "utilization_ratio",
            "actual_value": utilization_ratio,
        },
        "secondary": {
            "metric_key": "used_sheet_count",
            "actual_value": used_sheet_count,
        },
    }
    sb.tables["app.run_evaluations"].append(
        {
            "run_id": run_id,
            "scoring_profile_version_id": scoring_profile_version_id,
            "total_score": total_score,
            "evaluation_jsonb": {
                "input_metrics": {
                    "utilization_ratio": utilization_ratio,
                    "unplaced_ratio": unplaced_ratio,
                    "used_sheet_count": used_sheet_count,
                    "estimated_process_time_s": estimated_process_time_s,
                },
                "tie_breaker_inputs": tie_breaker_inputs,
                "components": {"utilization_weight": {"status": "applied"}},
            },
            "created_at": "2026-03-26T10:02:00Z",
        }
    )


def test_multi_item_ranking_success() -> None:
    print("\n=== 1. Multi-item ranking success ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(sb, owner=OWNER_A, tie_breaker_jsonb={"primary": "utilization_ratio"})

    run_a = _seed_run(sb, project_id=project_id)
    run_b = _seed_run(sb, project_id=project_id)
    run_c = _seed_run(sb, project_id=project_id)

    _seed_batch_item(sb, batch_id=batch_id, run_id=run_a, candidate_label="baseline", scoring_profile_version_id=version_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_b, candidate_label="aggressive", scoring_profile_version_id=version_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_c, candidate_label="balanced", scoring_profile_version_id=version_id)

    _seed_evaluation(
        sb,
        run_id=run_a,
        scoring_profile_version_id=version_id,
        total_score=0.91,
        utilization_ratio=0.88,
        unplaced_ratio=0.04,
        used_sheet_count=2.0,
        estimated_process_time_s=50.0,
    )
    _seed_evaluation(
        sb,
        run_id=run_b,
        scoring_profile_version_id=version_id,
        total_score=0.82,
        utilization_ratio=0.79,
        unplaced_ratio=0.06,
        used_sheet_count=2.0,
        estimated_process_time_s=58.0,
    )
    _seed_evaluation(
        sb,
        run_id=run_c,
        scoring_profile_version_id=version_id,
        total_score=0.75,
        utilization_ratio=0.74,
        unplaced_ratio=0.08,
        used_sheet_count=3.0,
        estimated_process_time_s=62.0,
    )

    result = create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )

    rows = result.get("items") if isinstance(result.get("items"), list) else []
    _test("three ranking rows persisted", len(rows) == 3)
    _test("was_replaced false on first ranking", not bool(result.get("was_replaced")))
    _test("total returned", int(result.get("total") or 0) == 3)

    rank_values = [int(row.get("rank_no") or 0) for row in rows if isinstance(row, dict)]
    _test("rank_no sequence is 1..N", rank_values == [1, 2, 3])
    _test("rank_no unique", len(set(rank_values)) == len(rank_values))
    _test("top run is highest score", str(rows[0].get("run_id") or "") == run_a)

    reason = rows[0].get("ranking_reason_jsonb") if isinstance(rows[0].get("ranking_reason_jsonb"), dict) else {}
    _test("reason contains tie_break_trace", isinstance(reason.get("tie_break_trace"), dict))
    _test("reason marks persisted score source", bool((reason.get("evaluation_summary_ref") or {}).get("score_is_persisted")))


def test_re_ranking_replaces_previous_set() -> None:
    print("\n=== 2. Re-ranking replaces previous set ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(sb, owner=OWNER_A, tie_breaker_jsonb={"primary": "utilization_ratio"})

    run_a = _seed_run(sb, project_id=project_id)
    run_b = _seed_run(sb, project_id=project_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_a, candidate_label="a", scoring_profile_version_id=version_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_b, candidate_label="b", scoring_profile_version_id=version_id)

    _seed_evaluation(
        sb,
        run_id=run_a,
        scoring_profile_version_id=version_id,
        total_score=0.60,
        utilization_ratio=0.7,
        unplaced_ratio=0.1,
        used_sheet_count=3.0,
        estimated_process_time_s=65.0,
    )
    _seed_evaluation(
        sb,
        run_id=run_b,
        scoring_profile_version_id=version_id,
        total_score=0.59,
        utilization_ratio=0.69,
        unplaced_ratio=0.1,
        used_sheet_count=3.0,
        estimated_process_time_s=65.0,
    )

    first = create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    first_top = str(((first.get("items") or [{}])[0]).get("run_id") or "")

    sb.tables["app.run_evaluations"][1]["total_score"] = 0.95
    second = create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    second_items = second.get("items") if isinstance(second.get("items"), list) else []
    second_top = str((second_items[0] if second_items else {}).get("run_id") or "")

    _test("second run marks replacement", bool(second.get("was_replaced")))
    _test("persisted row count remains two", len(sb.tables["app.run_ranking_results"]) == 2)
    _test("top run changed after score update", first_top != second_top and second_top == run_b)


def test_deterministic_tie_break_for_equal_total_score() -> None:
    print("\n=== 3. Deterministic tie-break on equal total_score ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(
        sb,
        owner=OWNER_A,
        tie_breaker_jsonb={"primary": "utilization_ratio", "secondary": "used_sheet_count"},
    )

    run_a = _seed_run(sb, project_id=project_id)
    run_b = _seed_run(sb, project_id=project_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_a, candidate_label="alpha", scoring_profile_version_id=version_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_b, candidate_label="beta", scoring_profile_version_id=version_id)

    _seed_evaluation(
        sb,
        run_id=run_a,
        scoring_profile_version_id=version_id,
        total_score=0.80,
        utilization_ratio=0.91,
        unplaced_ratio=0.05,
        used_sheet_count=2.0,
        estimated_process_time_s=44.0,
    )
    _seed_evaluation(
        sb,
        run_id=run_b,
        scoring_profile_version_id=version_id,
        total_score=0.80,
        utilization_ratio=0.84,
        unplaced_ratio=0.05,
        used_sheet_count=2.0,
        estimated_process_time_s=44.0,
    )

    first = create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    second = create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )

    first_order = [str(row.get("run_id") or "") for row in (first.get("items") or []) if isinstance(row, dict)]
    second_order = [str(row.get("run_id") or "") for row in (second.get("items") or []) if isinstance(row, dict)]
    _test("order deterministic across repeated ranking", first_order == second_order)
    _test("higher utilization wins tie", first_order[:1] == [run_a])


def test_missing_evaluation_fails_fast() -> None:
    print("\n=== 4. Missing evaluation fails fast ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(sb, owner=OWNER_A)

    run_a = _seed_run(sb, project_id=project_id)
    run_b = _seed_run(sb, project_id=project_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_a, candidate_label="has-eval", scoring_profile_version_id=version_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_b, candidate_label="missing-eval", scoring_profile_version_id=version_id)

    _seed_evaluation(
        sb,
        run_id=run_a,
        scoring_profile_version_id=version_id,
        total_score=0.5,
        utilization_ratio=0.7,
        unplaced_ratio=0.1,
        used_sheet_count=3.0,
        estimated_process_time_s=55.0,
    )

    try:
        create_or_replace_run_batch_ranking(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
        )
        _test("missing evaluation rejected", False, detail="should have raised")
    except RunRankingError as exc:
        _test("missing evaluation rejected", exc.status_code == 400)
        _test("missing evaluation mentions run_id", "missing run evaluation" in exc.detail)


def test_scoring_context_mismatch_fails() -> None:
    print("\n=== 5. Scoring context mismatch fails ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_batch = _seed_scoring_version(sb, owner=OWNER_A)
    version_eval = _seed_scoring_version(sb, owner=OWNER_A)

    run_a = _seed_run(sb, project_id=project_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_a, candidate_label="mismatch", scoring_profile_version_id=version_batch)
    _seed_evaluation(
        sb,
        run_id=run_a,
        scoring_profile_version_id=version_eval,
        total_score=0.81,
        utilization_ratio=0.8,
        unplaced_ratio=0.05,
        used_sheet_count=2.0,
        estimated_process_time_s=51.0,
    )

    try:
        create_or_replace_run_batch_ranking(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
        )
        _test("context mismatch rejected", False, detail="should have raised")
    except RunRankingError as exc:
        _test("context mismatch rejected", exc.status_code == 409)
        _test("context mismatch error text", "scoring context mismatch" in exc.detail)


def test_foreign_owner_batch_forbidden() -> None:
    print("\n=== 6. Foreign owner batch forbidden ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(sb, owner=OWNER_A)
    run_id = _seed_run(sb, project_id=project_id)
    _seed_batch_item(sb, batch_id=batch_id, run_id=run_id, candidate_label="owner-guard", scoring_profile_version_id=version_id)
    _seed_evaluation(
        sb,
        run_id=run_id,
        scoring_profile_version_id=version_id,
        total_score=0.61,
        utilization_ratio=0.75,
        unplaced_ratio=0.09,
        used_sheet_count=3.0,
        estimated_process_time_s=55.0,
    )

    try:
        create_or_replace_run_batch_ranking(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_B,
            project_id=project_id,
            batch_id=batch_id,
        )
        _test("foreign owner rejected", False, detail="should have raised")
    except RunRankingError as exc:
        _test("foreign owner rejected", exc.status_code == 404)


def test_no_side_effect_writes_outside_ranking_truth() -> None:
    print("\n=== 7. No side effects outside ranking truth ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(sb, owner=OWNER_A)
    run_id = _seed_run(sb, project_id=project_id)

    _seed_batch_item(sb, batch_id=batch_id, run_id=run_id, candidate_label="scope-check", scoring_profile_version_id=version_id)
    _seed_evaluation(
        sb,
        run_id=run_id,
        scoring_profile_version_id=version_id,
        total_score=0.88,
        utilization_ratio=0.83,
        unplaced_ratio=0.03,
        used_sheet_count=2.0,
        estimated_process_time_s=48.0,
    )

    sb.write_log.clear()
    create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )

    written_tables = {str(entry.get("table") or "") for entry in sb.write_log}
    _test("run_ranking_results written", "app.run_ranking_results" in written_tables)

    blocked_tables = {
        "app.run_evaluations",
        "app.project_selected_runs",
        "app.run_comparison_results",
        "app.run_business_metrics",
        "app.run_batches",
        "app.run_batch_items",
    }
    _test("no blocked table writes", not any(table_name in written_tables for table_name in blocked_tables))


def test_list_and_delete_ranking_contract() -> None:
    print("\n=== 8. List and delete ranking contract ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    batch_id = _seed_batch(sb, project_id=project_id, owner=OWNER_A)
    version_id = _seed_scoring_version(sb, owner=OWNER_A)
    run_id = _seed_run(sb, project_id=project_id)

    _seed_batch_item(sb, batch_id=batch_id, run_id=run_id, candidate_label="contract", scoring_profile_version_id=version_id)
    _seed_evaluation(
        sb,
        run_id=run_id,
        scoring_profile_version_id=version_id,
        total_score=0.66,
        utilization_ratio=0.7,
        unplaced_ratio=0.08,
        used_sheet_count=2.0,
        estimated_process_time_s=42.0,
    )
    create_or_replace_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )

    listed = list_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    _test("list returns one row", int(listed.get("total") or 0) == 1)

    deleted = delete_run_batch_ranking(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        batch_id=batch_id,
    )
    _test("delete returns deleted count", int(deleted.get("total_deleted") or 0) == 1)
    _test("ranking table empty after delete", len(sb.tables["app.run_ranking_results"]) == 0)

    try:
        delete_run_batch_ranking(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            batch_id=batch_id,
        )
        _test("second delete should fail", False, detail="should have raised")
    except RunRankingError as exc:
        _test("second delete fails with 404", exc.status_code == 404)


if __name__ == "__main__":
    print("H3-E3-T2 smoke: ranking engine\n")

    test_multi_item_ranking_success()
    test_re_ranking_replaces_previous_set()
    test_deterministic_tie_break_for_equal_total_score()
    test_missing_evaluation_fails_fast()
    test_scoring_context_mismatch_fails()
    test_foreign_owner_batch_forbidden()
    test_no_side_effect_writes_outside_ranking_truth()
    test_list_and_delete_ranking_contract()

    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{total} passed, {failed} failed")
    if failed:
        print("SMOKE FAIL", file=sys.stderr)
        raise SystemExit(1)

    print("SMOKE PASS")
    raise SystemExit(0)
