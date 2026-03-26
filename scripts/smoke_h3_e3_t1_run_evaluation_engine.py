#!/usr/bin/env python3
"""H3-E3-T1 smoke: run evaluation engine service."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_evaluations import (  # noqa: E402
    RunEvaluationError,
    create_or_replace_run_evaluation,
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
            "app.scoring_profile_versions": [],
            "app.project_scoring_selection": [],
            "app.run_metrics": [],
            "app.run_manufacturing_metrics": [],
            "app.run_evaluations": [],
            "app.run_ranking_results": [],
            "app.run_batches": [],
            "app.run_batch_items": [],
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
                column = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda row, col=column: str(row.get(col) or ""), reverse=reverse)

        limit_raw = str(params.get("limit") or "").strip()
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return rows

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        _ = access_token
        row = dict(payload)

        if table == "app.run_evaluations":
            run_id = str(row.get("run_id") or "").strip()
            for existing in self.tables["app.run_evaluations"]:
                if str(existing.get("run_id") or "").strip() == run_id:
                    raise SupabaseHTTPError("duplicate key value violates unique constraint run_evaluations_pkey")

        if "id" not in row and table in {"app.projects", "app.nesting_runs", "app.scoring_profile_versions"}:
            row["id"] = str(uuid4())

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
            if all(self._match_filter(row.get(key), flt) for key, flt in filters.items()):
                row.update(payload)
                updated.append(dict(row))
        self.write_log.append({"op": "update", "table": table, "payload": dict(payload), "filters": dict(filters)})
        return updated

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        _ = access_token
        remaining: list[dict[str, Any]] = []
        for row in self.tables.get(table, []):
            if all(self._match_filter(row.get(key), flt) for key, flt in filters.items()):
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


def _seed_run(sb: FakeSupabaseClient, *, owner: str, project_id: str) -> str:
    run_id = str(uuid4())
    sb.tables["app.nesting_runs"].append(
        {
            "id": run_id,
            "owner_user_id": owner,
            "project_id": project_id,
            "status": "done",
        }
    )
    return run_id


def _seed_scoring_version(
    sb: FakeSupabaseClient,
    *,
    owner: str,
    weights_jsonb: dict[str, Any] | None = None,
    threshold_jsonb: dict[str, Any] | None = None,
    tie_breaker_jsonb: dict[str, Any] | None = None,
    is_active: bool = True,
) -> str:
    version_id = str(uuid4())
    sb.tables["app.scoring_profile_versions"].append(
        {
            "id": version_id,
            "scoring_profile_id": str(uuid4()),
            "owner_user_id": owner,
            "version_no": 1,
            "lifecycle": "draft",
            "is_active": is_active,
            "weights_jsonb": dict(weights_jsonb or {}),
            "threshold_jsonb": dict(threshold_jsonb or {}),
            "tie_breaker_jsonb": dict(tie_breaker_jsonb or {}),
        }
    )
    return version_id


def _seed_run_metrics(
    sb: FakeSupabaseClient,
    *,
    run_id: str,
    placed_count: int,
    unplaced_count: int,
    used_sheet_count: int,
    utilization_ratio: float,
    remnant_value: float | None,
) -> None:
    sb.tables["app.run_metrics"].append(
        {
            "run_id": run_id,
            "placed_count": placed_count,
            "unplaced_count": unplaced_count,
            "used_sheet_count": used_sheet_count,
            "utilization_ratio": utilization_ratio,
            "remnant_value": remnant_value,
            "metrics_jsonb": {},
            "created_at": "2026-03-26T10:00:00Z",
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
            "estimated_cut_length_mm": 100.0,
            "estimated_rapid_length_mm": 20.0,
            "pierce_count": 3,
            "metrics_jsonb": {},
            "created_at": "2026-03-26T10:00:05Z",
        }
    )


def _seed_project_scoring_selection(
    sb: FakeSupabaseClient,
    *,
    project_id: str,
    version_id: str,
    selected_by: str,
) -> None:
    sb.tables["app.project_scoring_selection"].append(
        {
            "project_id": project_id,
            "active_scoring_profile_version_id": version_id,
            "selected_at": "2026-03-26T09:59:59Z",
            "selected_by": selected_by,
        }
    )


def test_explicit_version_success() -> None:
    print("\n=== 1. Explicit scoring version path works ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=90,
        unplaced_count=10,
        used_sheet_count=3,
        utilization_ratio=0.82,
        remnant_value=120.0,
    )
    _seed_manufacturing_metrics(sb, run_id=run_id, estimated_process_time_s=55.0)

    version_id = _seed_scoring_version(
        sb,
        owner=OWNER_A,
        weights_jsonb={
            "utilization_weight": 0.4,
            "unplaced_penalty": 0.2,
            "sheet_count_penalty": 0.1,
            "remnant_value_weight": 0.1,
            "process_time_penalty": 0.1,
            "priority_fulfilment_weight": 0.05,
            "inventory_consumption_penalty": 0.05,
        },
        threshold_jsonb={
            "max_estimated_process_time_s": 100.0,
            "max_remnant_value": 200.0,
            "min_utilization": 0.6,
            "max_unplaced_ratio": 0.2,
            "max_used_sheet_count": 6,
            "min_remnant_value": 50.0,
        },
        tie_breaker_jsonb={
            "primary": "utilization",
            "secondary": "used_sheet_count",
            "unknown": "x",
        },
    )

    result = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )

    row = result.get("evaluation") or {}
    payload = row.get("evaluation_jsonb") if isinstance(row.get("evaluation_jsonb"), dict) else {}

    _test("result has evaluation row", isinstance(row, dict))
    _test("resolved from explicit version", not bool(result.get("resolved_from_project_selection")))
    _test("persisted version id matches", str(row.get("scoring_profile_version_id") or "") == version_id)
    _test("exactly one run_evaluations row", len(sb.tables["app.run_evaluations"]) == 1)
    _test("score is bounded", -1.0 <= float(row.get("total_score") or 0.0) <= 1.0)

    components = payload.get("components") if isinstance(payload.get("components"), dict) else {}
    _test("components include utilization", "utilization_weight" in components)
    _test("unsupported component tracked", "priority_fulfilment_weight" in components)
    _test(
        "unsupported contribution is zero",
        float((components.get("priority_fulfilment_weight") or {}).get("contribution", -1.0)) == 0.0,
    )

    threshold_results = payload.get("threshold_results") if isinstance(payload.get("threshold_results"), dict) else {}
    _test("threshold results include known key", "max_unplaced_ratio" in threshold_results)


def test_re_evaluation_replaces_existing_row() -> None:
    print("\n=== 2. Re-evaluation replaces existing row ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=50,
        unplaced_count=5,
        used_sheet_count=2,
        utilization_ratio=0.7,
        remnant_value=80.0,
    )
    _seed_manufacturing_metrics(sb, run_id=run_id, estimated_process_time_s=70.0)
    version_id = _seed_scoring_version(
        sb,
        owner=OWNER_A,
        weights_jsonb={"utilization_weight": 1.0, "unplaced_penalty": 1.0, "sheet_count_penalty": 1.0},
    )

    first = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )
    first_score = float((first.get("evaluation") or {}).get("total_score") or 0.0)

    sb.tables["app.run_metrics"][0]["utilization_ratio"] = 0.9
    second = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )
    second_score = float((second.get("evaluation") or {}).get("total_score") or 0.0)

    _test("second call marked as replace", bool(second.get("was_replaced")))
    _test("still one persisted evaluation row", len(sb.tables["app.run_evaluations"]) == 1)
    _test("score changed after metrics change", first_score != second_score)


def test_deterministic_for_identical_input() -> None:
    print("\n=== 3. Deterministic score on identical input ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=40,
        unplaced_count=8,
        used_sheet_count=4,
        utilization_ratio=0.75,
        remnant_value=100.0,
    )
    _seed_manufacturing_metrics(sb, run_id=run_id, estimated_process_time_s=60.0)
    version_id = _seed_scoring_version(
        sb,
        owner=OWNER_A,
        weights_jsonb={
            "utilization_weight": 0.5,
            "unplaced_penalty": 0.2,
            "sheet_count_penalty": 0.2,
            "process_time_penalty": 0.1,
        },
        threshold_jsonb={"max_estimated_process_time_s": 120.0},
    )

    first = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )
    second = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )

    first_eval = first.get("evaluation") if isinstance(first.get("evaluation"), dict) else {}
    second_eval = second.get("evaluation") if isinstance(second.get("evaluation"), dict) else {}
    first_payload = first_eval.get("evaluation_jsonb") if isinstance(first_eval.get("evaluation_jsonb"), dict) else {}
    second_payload = second_eval.get("evaluation_jsonb") if isinstance(second_eval.get("evaluation_jsonb"), dict) else {}

    _test("total_score deterministic", first_eval.get("total_score") == second_eval.get("total_score"))
    _test(
        "component breakdown deterministic",
        (first_payload.get("components") if isinstance(first_payload.get("components"), dict) else {})
        == (second_payload.get("components") if isinstance(second_payload.get("components"), dict) else {}),
    )


def test_missing_run_metrics_fails() -> None:
    print("\n=== 4. Missing run_metrics causes error ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    version_id = _seed_scoring_version(sb, owner=OWNER_A, weights_jsonb={"utilization_weight": 1.0})

    try:
        create_or_replace_run_evaluation(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            run_id=run_id,
            scoring_profile_version_id=version_id,
        )
        _test("missing metrics rejected", False, detail="should have raised")
    except RunEvaluationError as exc:
        _test("missing metrics rejected", exc.status_code == 400)


def test_missing_manufacturing_metrics_marks_not_applied() -> None:
    print("\n=== 5. Missing manufacturing metric keeps H1 scoring path ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=12,
        unplaced_count=3,
        used_sheet_count=2,
        utilization_ratio=0.66,
        remnant_value=10.0,
    )
    version_id = _seed_scoring_version(
        sb,
        owner=OWNER_A,
        weights_jsonb={"utilization_weight": 0.7, "process_time_penalty": 0.3},
        threshold_jsonb={"max_estimated_process_time_s": 200.0},
    )

    result = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )
    payload = (result.get("evaluation") or {}).get("evaluation_jsonb")
    components = payload.get("components") if isinstance(payload, dict) and isinstance(payload.get("components"), dict) else {}
    process_component = components.get("process_time_penalty") or {}

    _test("process_time_penalty not applied", str(process_component.get("status") or "") == "not_applied")
    _test("process_time_penalty marks missing_metric", str(process_component.get("detail") or "") == "missing_metric")
    _test("h1 utilization component still applied", str((components.get("utilization_weight") or {}).get("status") or "") == "applied")


def test_foreign_owner_version_rejected() -> None:
    print("\n=== 6. Foreign owner scoring version rejected ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=10,
        unplaced_count=0,
        used_sheet_count=1,
        utilization_ratio=0.9,
        remnant_value=None,
    )
    foreign_version_id = _seed_scoring_version(sb, owner=OWNER_B, weights_jsonb={"utilization_weight": 1.0})

    try:
        create_or_replace_run_evaluation(
            supabase=sb,
            access_token=TOKEN,
            owner_user_id=OWNER_A,
            project_id=project_id,
            run_id=run_id,
            scoring_profile_version_id=foreign_version_id,
        )
        _test("foreign version rejected", False, detail="should have raised")
    except RunEvaluationError as exc:
        _test("foreign version rejected", exc.status_code == 403)


def test_project_selection_fallback() -> None:
    print("\n=== 7. Project selection fallback works ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=25,
        unplaced_count=5,
        used_sheet_count=2,
        utilization_ratio=0.8,
        remnant_value=30.0,
    )
    version_id = _seed_scoring_version(sb, owner=OWNER_A, weights_jsonb={"utilization_weight": 1.0})
    _seed_project_scoring_selection(sb, project_id=project_id, version_id=version_id, selected_by=OWNER_A)

    result = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=None,
    )
    row = result.get("evaluation") if isinstance(result.get("evaluation"), dict) else {}

    _test("fallback path flagged", bool(result.get("resolved_from_project_selection")))
    _test("fallback persists selected version", str(row.get("scoring_profile_version_id") or "") == version_id)


def test_unsupported_weights_zero_contribution() -> None:
    print("\n=== 8. Unsupported weights are explicit zero-contribution components ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=35,
        unplaced_count=7,
        used_sheet_count=3,
        utilization_ratio=0.77,
        remnant_value=70.0,
    )
    version_id = _seed_scoring_version(
        sb,
        owner=OWNER_A,
        weights_jsonb={
            "utilization_weight": 0.8,
            "priority_fulfilment_weight": 0.15,
            "inventory_consumption_penalty": 0.05,
        },
    )

    result = create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )
    payload = (result.get("evaluation") or {}).get("evaluation_jsonb")
    components = payload.get("components") if isinstance(payload, dict) and isinstance(payload.get("components"), dict) else {}

    priority_component = components.get("priority_fulfilment_weight") or {}
    inventory_component = components.get("inventory_consumption_penalty") or {}

    _test("priority component marked unsupported", str(priority_component.get("status") or "") == "unsupported_metric")
    _test("priority contribution zero", float(priority_component.get("contribution", -1.0)) == 0.0)
    _test("inventory component marked unsupported", str(inventory_component.get("status") or "") == "unsupported_metric")
    _test("inventory contribution zero", float(inventory_component.get("contribution", -1.0)) == 0.0)


def test_no_ranking_batch_selection_write_side_effect() -> None:
    print("\n=== 9. No ranking/batch/selection write side effects ===")
    sb = FakeSupabaseClient()
    project_id = _seed_project(sb, owner=OWNER_A)
    run_id = _seed_run(sb, owner=OWNER_A, project_id=project_id)
    _seed_run_metrics(
        sb,
        run_id=run_id,
        placed_count=18,
        unplaced_count=2,
        used_sheet_count=1,
        utilization_ratio=0.91,
        remnant_value=None,
    )
    version_id = _seed_scoring_version(sb, owner=OWNER_A, weights_jsonb={"utilization_weight": 1.0})

    create_or_replace_run_evaluation(
        supabase=sb,
        access_token=TOKEN,
        owner_user_id=OWNER_A,
        project_id=project_id,
        run_id=run_id,
        scoring_profile_version_id=version_id,
    )

    written_tables = {str(entry.get("table") or "") for entry in sb.write_log}
    blocked_tables = {
        "app.run_ranking_results",
        "app.run_batches",
        "app.run_batch_items",
        "app.project_scoring_selection",
    }

    _test("run_evaluations written", "app.run_evaluations" in written_tables)
    _test("no blocked table writes", not any(table in written_tables for table in blocked_tables))


if __name__ == "__main__":
    test_explicit_version_success()
    test_re_evaluation_replaces_existing_row()
    test_deterministic_for_identical_input()
    test_missing_run_metrics_fails()
    test_missing_manufacturing_metrics_marks_not_applied()
    test_foreign_owner_version_rejected()
    test_project_selection_fallback()
    test_unsupported_weights_zero_contribution()
    test_no_ranking_batch_selection_write_side_effect()

    total = passed + failed
    print(f"\nSummary: {passed}/{total} passed")
    if failed:
        sys.exit(1)
