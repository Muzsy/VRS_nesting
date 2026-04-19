#!/usr/bin/env python3
"""H2-E4-T3 smoke: manufacturing metrics calculator — metrics truth layer."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.manufacturing_metrics_calculator import (  # noqa: E402
    calculate_manufacturing_metrics,
    ManufacturingMetricsCalculatorError,
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
            msg += f" — {detail}"
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Fake Supabase client (reuses H2-E4-T2 pattern)
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.nesting_runs": [],
            "app.run_manufacturing_plans": [],
            "app.run_manufacturing_contours": [],
            "app.geometry_contour_classes": [],
            "app.cut_contour_rules": [],
            "app.run_manufacturing_metrics": [],
            "app.run_artifacts": [],
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
        if "id" not in row and "run_id" not in row:
            row["id"] = str(uuid4())
        self.tables.setdefault(table, []).append(row)
        self.write_log.append({"op": "insert", "table": table, "payload": row})
        return row

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        self.write_log.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        return [dict(payload)]

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_log.append({"op": "delete", "table": table, "filters": filters})
        rows = self.tables.get(table, [])
        meta_keys = {"select", "order", "limit", "offset"}
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
# Seed helpers
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"


def _seed_full(fake: FakeSupabaseClient) -> dict[str, str]:
    """Seed a complete happy-path scenario with persisted manufacturing plan."""
    run_id = str(uuid4())
    plan_id = str(uuid4())
    sheet_id = str(uuid4())
    placement_id = str(uuid4())
    mfg_derivative_id = str(uuid4())
    contour_class_id_0 = str(uuid4())
    contour_class_id_1 = str(uuid4())
    rule_outer_id = str(uuid4())
    rule_inner_id = str(uuid4())
    cut_rule_set_id = str(uuid4())

    # Run
    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": str(uuid4()),
        "status": "succeeded",
    })

    # Persisted manufacturing plan
    fake.tables["app.run_manufacturing_plans"].append({
        "id": plan_id,
        "run_id": run_id,
        "sheet_id": sheet_id,
        "manufacturing_profile_version_id": str(uuid4()),
        "cut_rule_set_id": cut_rule_set_id,
        "status": "generated",
        "summary_jsonb": {"builder_scope": "h2_e4_t2", "placement_count": 1},
    })

    # Manufacturing contours (outer + inner)
    fake.tables["app.run_manufacturing_contours"].extend([
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "placement_id": placement_id,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_class_id": contour_class_id_0,
            "matched_rule_id": rule_outer_id,
            "contour_index": 0,
            "contour_kind": "outer",
            "feature_class": "default",
            "entry_point_jsonb": {"x": 10.0, "y": 20.0, "rotation_deg": 0.0, "source": "placement_transform"},
            "lead_in_jsonb": {"type": "line", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "line", "source": "matched_rule"},
            "cut_order_index": 0,
            "metadata_jsonb": {"builder_scope": "h2_e4_t2"},
        },
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "placement_id": placement_id,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_class_id": contour_class_id_1,
            "matched_rule_id": rule_inner_id,
            "contour_index": 1,
            "contour_kind": "inner",
            "feature_class": "default",
            "entry_point_jsonb": {"x": 50.0, "y": 60.0, "rotation_deg": 0.0, "source": "placement_transform"},
            "lead_in_jsonb": {"type": "arc", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "none", "source": "matched_rule"},
            "cut_order_index": 1,
            "metadata_jsonb": {"builder_scope": "h2_e4_t2"},
        },
    ])

    # Contour classes (with perimeter truth)
    fake.tables["app.geometry_contour_classes"].extend([
        {
            "id": contour_class_id_0,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_index": 0,
            "contour_kind": "outer",
            "feature_class": "default",
            "is_closed": True,
            "area_mm2": 5000.0,
            "perimeter_mm": 300.0,
        },
        {
            "id": contour_class_id_1,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_index": 1,
            "contour_kind": "inner",
            "feature_class": "default",
            "is_closed": True,
            "area_mm2": 400.0,
            "perimeter_mm": 80.0,
        },
    ])

    # Cut contour rules (with pierce_count truth)
    fake.tables["app.cut_contour_rules"].extend([
        {
            "id": rule_outer_id,
            "cut_rule_set_id": cut_rule_set_id,
            "contour_kind": "outer",
            "feature_class": "default",
            "pierce_count": 1,
            "lead_in_type": "line",
            "lead_out_type": "line",
            "sort_order": 0,
            "enabled": True,
        },
        {
            "id": rule_inner_id,
            "cut_rule_set_id": cut_rule_set_id,
            "contour_kind": "inner",
            "feature_class": "default",
            "pierce_count": 2,
            "lead_in_type": "arc",
            "lead_out_type": "none",
            "sort_order": 0,
            "enabled": True,
        },
    ])

    return {
        "run_id": run_id,
        "plan_id": plan_id,
        "contour_class_id_0": contour_class_id_0,
        "contour_class_id_1": contour_class_id_1,
        "rule_outer_id": rule_outer_id,
        "rule_inner_id": rule_inner_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed
    import math as _math

    # ===================================================================
    # TEST 1: valid persisted plan -> metrics record created
    # ===================================================================
    print("Test 1: valid persisted plan -> metrics record created")
    fake1 = FakeSupabaseClient()
    ids1 = _seed_full(fake1)

    result1 = calculate_manufacturing_metrics(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
    )
    _test("result is dict", isinstance(result1, dict))
    _test("run_id correct", result1.get("run_id") == ids1["run_id"])

    metrics_rows = fake1.tables["app.run_manufacturing_metrics"]
    _test("1 metrics record persisted", len(metrics_rows) == 1)
    _test("metrics.run_id correct", metrics_rows[0].get("run_id") == ids1["run_id"])

    # ===================================================================
    # TEST 2: pierce_count computed from matched rule truth
    # ===================================================================
    print("\nTest 2: pierce_count from matched rule truth")
    # outer rule: pierce_count=1, inner rule: pierce_count=2 => total=3
    _test("pierce_count == 3", result1.get("pierce_count") == 3,
          f"got {result1.get('pierce_count')}")

    # ===================================================================
    # TEST 3: cut length from contour class perimeter truth
    # ===================================================================
    print("\nTest 3: cut length from contour class perimeter truth")
    # outer perimeter: 300.0, inner perimeter: 80.0 => total: 380.0
    expected_cut_length = 380.0
    actual_cut_length = float(result1.get("estimated_cut_length_mm") or 0)
    _test("estimated_cut_length_mm == 380.0",
          abs(actual_cut_length - expected_cut_length) < 0.01,
          f"got {actual_cut_length}")

    # ===================================================================
    # TEST 4: rapid length is deterministic proxy
    # ===================================================================
    print("\nTest 4: rapid length is deterministic proxy")
    # entry points: (10,20) -> (50,60), distance = sqrt(40^2 + 40^2) = sqrt(3200) ~ 56.5685
    expected_rapid = _math.sqrt(40.0**2 + 40.0**2)
    actual_rapid = float(result1.get("estimated_rapid_length_mm") or 0)
    _test("estimated_rapid_length_mm ~ 56.569",
          abs(actual_rapid - expected_rapid) < 0.01,
          f"got {actual_rapid}")

    # Determinism: run again and check same result
    fake1b = FakeSupabaseClient()
    ids1b = _seed_full(fake1b)
    result1b = calculate_manufacturing_metrics(
        supabase=fake1b,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1b["run_id"],
    )
    _test("rapid length deterministic across runs",
          float(result1b.get("estimated_rapid_length_mm") or 0) == actual_rapid)

    # ===================================================================
    # TEST 5: idempotent rebuild — no duplicates
    # ===================================================================
    print("\nTest 5: idempotent rebuild — no duplicates")
    result2 = calculate_manufacturing_metrics(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
    )
    metrics_after = fake1.tables["app.run_manufacturing_metrics"]
    _test("still 1 metrics record after rebuild", len(metrics_after) == 1)
    _test("rebuild pierce_count == 3", result2.get("pierce_count") == 3)
    _test("rebuild cut_length == 380.0",
          abs(float(result2.get("estimated_cut_length_mm") or 0) - 380.0) < 0.01)

    # ===================================================================
    # TEST 6: no write to earlier truth tables
    # ===================================================================
    print("\nTest 6: no write to earlier truth tables")
    forbidden_tables = {
        "app.geometry_contour_classes",
        "app.cut_contour_rules",
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.nesting_runs",
    }
    for entry in fake1.write_log:
        table = entry.get("table", "")
        op = entry.get("op", "")
        if op == "delete" and table == "app.run_manufacturing_metrics":
            continue  # idempotent delete is allowed
        _test(f"no write to {table}", table not in forbidden_tables,
              f"op={op} table={table}")

    # ===================================================================
    # TEST 7: no preview/export artifact
    # ===================================================================
    print("\nTest 7: no preview/export artifact")
    artifact_writes = [
        e for e in fake1.write_log
        if e.get("table") == "app.run_artifacts"
    ]
    _test("no run_artifacts writes", len(artifact_writes) == 0,
          f"artifact_writes={artifact_writes}")

    # ===================================================================
    # TEST 8: contour counts correct
    # ===================================================================
    print("\nTest 8: contour counts correct")
    _test("outer_contour_count == 1", result1.get("outer_contour_count") == 1)
    _test("inner_contour_count == 1", result1.get("inner_contour_count") == 1)

    # ===================================================================
    # TEST 9: process time proxy uses documented formula
    # ===================================================================
    print("\nTest 9: process time proxy formula")
    # cut_time = 380.0 / 50.0 = 7.6 s
    # rapid_time = 56.5685... / 200.0 = 0.2828... s
    # pierce_time = 3 * 0.5 = 1.5 s
    # total ~ 9.3828...
    cut_time = 380.0 / 50.0
    rapid_time = expected_rapid / 200.0
    pierce_time = 3 * 0.5
    expected_process_time = cut_time + rapid_time + pierce_time
    actual_process_time = float(result1.get("estimated_process_time_s") or 0)
    _test("estimated_process_time_s matches formula",
          abs(actual_process_time - expected_process_time) < 0.01,
          f"expected={expected_process_time:.4f} got={actual_process_time:.4f}")

    # ===================================================================
    # TEST 10: metrics_jsonb has auditable structure
    # ===================================================================
    print("\nTest 10: metrics_jsonb auditable structure")
    mjsonb = result1.get("metrics_jsonb", {})
    _test("metrics_jsonb.calculator_scope == h2_e4_t3",
          mjsonb.get("calculator_scope") == "h2_e4_t3")
    _test("metrics_jsonb.contour_count_by_kind present",
          isinstance(mjsonb.get("contour_count_by_kind"), dict))
    _test("metrics_jsonb.cut_length_by_contour_kind present",
          isinstance(mjsonb.get("cut_length_by_contour_kind"), dict))
    _test("metrics_jsonb.timing_model present",
          isinstance(mjsonb.get("timing_model"), dict))
    _test("metrics_jsonb.timing_assumptions present",
          isinstance(mjsonb.get("timing_assumptions"), dict))
    _test("timing_assumptions.cut_speed_mm_s == 50.0",
          mjsonb.get("timing_assumptions", {}).get("cut_speed_mm_s") == 50.0)
    _test("timing_assumptions.rapid_speed_mm_s == 200.0",
          mjsonb.get("timing_assumptions", {}).get("rapid_speed_mm_s") == 200.0)
    _test("timing_assumptions.pierce_time_s_per_pierce == 0.5",
          mjsonb.get("timing_assumptions", {}).get("pierce_time_s_per_pierce") == 0.5)

    # ===================================================================
    # TEST 11: run not owned by user -> error
    # ===================================================================
    print("\nTest 11: run not owned by user -> error")
    fake11 = FakeSupabaseClient()
    ids11 = _seed_full(fake11)
    err11 = False
    try:
        calculate_manufacturing_metrics(
            supabase=fake11,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id="other-user-id",
            run_id=ids11["run_id"],
        )
    except ManufacturingMetricsCalculatorError as exc:
        err11 = "not found" in exc.detail or "not owned" in exc.detail
    _test("wrong owner -> error", err11)

    # ===================================================================
    # TEST 12: no manufacturing plan -> error
    # ===================================================================
    print("\nTest 12: no manufacturing plan -> error")
    fake12 = FakeSupabaseClient()
    run_id_12 = str(uuid4())
    fake12.tables["app.nesting_runs"].append({
        "id": run_id_12,
        "owner_user_id": OWNER_ID,
        "project_id": str(uuid4()),
        "status": "succeeded",
    })
    err12 = False
    try:
        calculate_manufacturing_metrics(
            supabase=fake12,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=run_id_12,
        )
    except ManufacturingMetricsCalculatorError as exc:
        err12 = "no persisted manufacturing plans" in exc.detail
    _test("no manufacturing plan -> error", err12)

    # ===================================================================
    # TEST 13: missing run_id -> error
    # ===================================================================
    print("\nTest 13: missing run_id -> error")
    fake13 = FakeSupabaseClient()
    err13 = False
    try:
        calculate_manufacturing_metrics(
            supabase=fake13,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id="",
        )
    except ManufacturingMetricsCalculatorError as exc:
        err13 = "run_id" in exc.detail
    _test("empty run_id -> error", err13)

    # ===================================================================
    # TEST 14: cut_length_by_contour_kind breakdown
    # ===================================================================
    print("\nTest 14: cut_length_by_contour_kind breakdown")
    cut_by_kind = mjsonb.get("cut_length_by_contour_kind", {})
    _test("outer_mm == 300.0",
          abs(float(cut_by_kind.get("outer_mm", 0)) - 300.0) < 0.01)
    _test("inner_mm == 80.0",
          abs(float(cut_by_kind.get("inner_mm", 0)) - 80.0) < 0.01)
    _test("total_mm == 380.0",
          abs(float(cut_by_kind.get("total_mm", 0)) - 380.0) < 0.01)

    # ===================================================================
    # Summary
    # ===================================================================
    total = passed + failed
    print(f"\n{'=' * 60}")
    if failed == 0:
        print(f"[PASS] smoke_h2_e4_t3_manufacturing_metrics_calculator: {passed}/{total} tests passed")
        return 0
    else:
        print(
            f"[FAIL] smoke_h2_e4_t3_manufacturing_metrics_calculator: {passed}/{total} passed, {failed} failed",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
