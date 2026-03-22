#!/usr/bin/env python3
"""H2-E4-T2 smoke: manufacturing plan builder — plan truth layer."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.manufacturing_plan_builder import (  # noqa: E402
    build_manufacturing_plan,
    ManufacturingPlanBuilderError,
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
# Fake Supabase client (extends H2-E4-T1 pattern)
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.nesting_runs": [],
            "app.nesting_run_snapshots": [],
            "app.run_layout_sheets": [],
            "app.run_layout_placements": [],
            "app.part_revisions": [],
            "app.geometry_derivatives": [],
            "app.geometry_contour_classes": [],
            "app.cut_rule_sets": [],
            "app.cut_contour_rules": [],
            "app.run_manufacturing_plans": [],
            "app.run_manufacturing_contours": [],
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
        if normalized.startswith("gt."):
            try:
                return float(value) > float(normalized[3:])
            except (TypeError, ValueError):
                return False
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
        self.write_log.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        return [dict(payload)]

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_log.append({"op": "delete", "table": table, "filters": filters})
        # Actually remove from tables for idempotency testing
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
        # Cascade: delete contours if plans deleted
        if table == "app.run_manufacturing_plans":
            deleted_plan_ids = {
                str(r.get("id") or "")
                for r in rows
                if r not in remaining
            }
            if deleted_plan_ids:
                self.tables["app.run_manufacturing_contours"] = [
                    c for c in self.tables.get("app.run_manufacturing_contours", [])
                    if str(c.get("manufacturing_plan_id") or "") not in deleted_plan_ids
                ]


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"


def _seed_full(fake: FakeSupabaseClient) -> dict[str, str]:
    """Seed a complete happy-path scenario with run + projection + manufacturing data."""
    run_id = str(uuid4())
    snapshot_id = str(uuid4())
    sheet_id = str(uuid4())
    placement_id = str(uuid4())
    part_revision_id = str(uuid4())
    mfg_derivative_id = str(uuid4())
    geo_rev_id = str(uuid4())
    contour_class_id_0 = str(uuid4())
    contour_class_id_1 = str(uuid4())
    cut_rule_set_id = str(uuid4())
    rule_outer_id = str(uuid4())
    rule_inner_id = str(uuid4())
    mfg_profile_version_id = str(uuid4())

    # Run
    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": str(uuid4()),
        "status": "succeeded",
    })

    # Snapshot with manufacturing selection
    fake.tables["app.nesting_run_snapshots"].append({
        "id": snapshot_id,
        "run_id": run_id,
        "includes_manufacturing": True,
        "manufacturing_manifest_jsonb": {
            "mode": "h2_e4_t1_snapshot_selection",
            "selection_present": True,
            "active_manufacturing_profile_version_id": mfg_profile_version_id,
            "manufacturing_profile_version": {
                "manufacturing_profile_id": str(uuid4()),
                "version_no": 1,
                "lifecycle": "approved",
                "is_active": True,
            },
            "postprocess_selection_present": False,
        },
    })

    # Projection: 1 sheet, 1 placement
    fake.tables["app.run_layout_sheets"].append({
        "id": sheet_id,
        "run_id": run_id,
        "sheet_index": 0,
        "sheet_revision_id": str(uuid4()),
        "width_mm": 3000.0,
        "height_mm": 1500.0,
        "metadata_jsonb": {},
    })
    fake.tables["app.run_layout_placements"].append({
        "id": placement_id,
        "run_id": run_id,
        "sheet_id": sheet_id,
        "placement_index": 0,
        "part_revision_id": part_revision_id,
        "transform_jsonb": {"x": 10.0, "y": 20.0, "rotation_deg": 0.0},
        "bbox_jsonb": {},
        "metadata_jsonb": {},
    })

    # Part revision with manufacturing derivative
    fake.tables["app.part_revisions"].append({
        "id": part_revision_id,
        "selected_manufacturing_derivative_id": mfg_derivative_id,
    })

    # Manufacturing canonical derivative
    fake.tables["app.geometry_derivatives"].append({
        "id": mfg_derivative_id,
        "geometry_revision_id": geo_rev_id,
        "derivative_kind": "manufacturing_canonical",
        "derivative_jsonb": {
            "contours": [
                {"contour_index": 0, "contour_role": "outer", "winding": "ccw",
                 "points": [[0, 0], [100, 0], [100, 50], [0, 50], [0, 0]]},
                {"contour_index": 1, "contour_role": "hole", "winding": "cw",
                 "points": [[10, 10], [30, 10], [30, 30], [10, 30], [10, 10]]},
            ],
        },
    })

    # Contour classification
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

    # Cut rule set + rules
    fake.tables["app.cut_rule_sets"].append({
        "id": cut_rule_set_id,
        "owner_user_id": OWNER_ID,
        "name": "Test Rules",
    })
    fake.tables["app.cut_contour_rules"].extend([
        {
            "id": rule_outer_id,
            "cut_rule_set_id": cut_rule_set_id,
            "contour_kind": "outer",
            "feature_class": "default",
            "lead_in_type": "line",
            "lead_out_type": "line",
            "sort_order": 0,
            "enabled": True,
            "min_contour_length_mm": None,
            "max_contour_length_mm": None,
        },
        {
            "id": rule_inner_id,
            "cut_rule_set_id": cut_rule_set_id,
            "contour_kind": "inner",
            "feature_class": "default",
            "lead_in_type": "arc",
            "lead_out_type": "none",
            "sort_order": 0,
            "enabled": True,
            "min_contour_length_mm": None,
            "max_contour_length_mm": None,
        },
    ])

    return {
        "run_id": run_id,
        "cut_rule_set_id": cut_rule_set_id,
        "sheet_id": sheet_id,
        "placement_id": placement_id,
        "mfg_derivative_id": mfg_derivative_id,
        "rule_outer_id": rule_outer_id,
        "rule_inner_id": rule_inner_id,
        "contour_class_id_0": contour_class_id_0,
        "contour_class_id_1": contour_class_id_1,
        "mfg_profile_version_id": mfg_profile_version_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed

    # ===================================================================
    # TEST 1: valid input -> plan + contours created
    # ===================================================================
    print("Test 1: valid input -> plan + contours created")
    fake1 = FakeSupabaseClient()
    ids1 = _seed_full(fake1)

    result1 = build_manufacturing_plan(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
        cut_rule_set_id=ids1["cut_rule_set_id"],
    )
    _test("result is dict", isinstance(result1, dict))
    _test("plans_created == 1", result1.get("plans_created") == 1)
    _test("contours_created == 2", result1.get("contours_created") == 2)

    plans = fake1.tables["app.run_manufacturing_plans"]
    _test("1 plan record persisted", len(plans) == 1)
    _test("plan.run_id correct", plans[0].get("run_id") == ids1["run_id"])
    _test("plan.sheet_id correct", plans[0].get("sheet_id") == ids1["sheet_id"])
    _test("plan.cut_rule_set_id correct", plans[0].get("cut_rule_set_id") == ids1["cut_rule_set_id"])
    _test("plan.manufacturing_profile_version_id correct",
          plans[0].get("manufacturing_profile_version_id") == ids1["mfg_profile_version_id"])
    _test("plan.status is generated", plans[0].get("status") == "generated")

    contours = fake1.tables["app.run_manufacturing_contours"]
    _test("2 contour records persisted", len(contours) == 2)

    # ===================================================================
    # TEST 2: contour records have matched rule references
    # ===================================================================
    print("\nTest 2: contour records have matched rule references")
    outer_contour = next((c for c in contours if c.get("contour_kind") == "outer"), None)
    inner_contour = next((c for c in contours if c.get("contour_kind") == "inner"), None)

    _test("outer contour exists", outer_contour is not None)
    _test("inner contour exists", inner_contour is not None)

    if outer_contour:
        _test("outer.matched_rule_id == rule_outer_id",
              outer_contour.get("matched_rule_id") == ids1["rule_outer_id"])
        _test("outer.contour_class_id set",
              outer_contour.get("contour_class_id") == ids1["contour_class_id_0"])
        _test("outer.geometry_derivative_id set",
              outer_contour.get("geometry_derivative_id") == ids1["mfg_derivative_id"])

    if inner_contour:
        _test("inner.matched_rule_id == rule_inner_id",
              inner_contour.get("matched_rule_id") == ids1["rule_inner_id"])
        _test("inner.contour_class_id set",
              inner_contour.get("contour_class_id") == ids1["contour_class_id_1"])

    # ===================================================================
    # TEST 3: entry/lead/cut-order info present
    # ===================================================================
    print("\nTest 3: entry/lead/cut-order info present")
    for contour in contours:
        ci = contour.get("contour_index")
        _test(f"contour[{ci}].entry_point_jsonb is dict",
              isinstance(contour.get("entry_point_jsonb"), dict))
        _test(f"contour[{ci}].lead_in_jsonb is dict",
              isinstance(contour.get("lead_in_jsonb"), dict))
        _test(f"contour[{ci}].lead_out_jsonb is dict",
              isinstance(contour.get("lead_out_jsonb"), dict))
        _test(f"contour[{ci}].cut_order_index is int",
              isinstance(contour.get("cut_order_index"), int))

    # cut_order_index deterministic and monotonic
    cut_orders = sorted(c.get("cut_order_index", -1) for c in contours)
    _test("cut_order_index values are 0,1", cut_orders == [0, 1])

    # ===================================================================
    # TEST 4: no write to earlier truth tables
    # ===================================================================
    print("\nTest 4: no write to earlier truth tables")
    forbidden_tables = {
        "app.geometry_contour_classes",
        "app.cut_contour_rules",
        "app.cut_rule_sets",
        "app.nesting_runs",
        "app.nesting_run_snapshots",
        "app.run_layout_sheets",
        "app.run_layout_placements",
    }
    for entry in fake1.write_log:
        table = entry.get("table", "")
        op = entry.get("op", "")
        if op == "delete" and table == "app.run_manufacturing_plans":
            continue  # idempotent delete is allowed
        _test(f"no write to {table}", table not in forbidden_tables,
              f"op={op} table={table}")

    # ===================================================================
    # TEST 5: no preview/export artifact
    # ===================================================================
    print("\nTest 5: no preview/export artifact")
    artifact_writes = [
        e for e in fake1.write_log
        if e.get("table") == "app.run_artifacts"
    ]
    _test("no run_artifacts writes", len(artifact_writes) == 0,
          f"artifact_writes={artifact_writes}")

    # ===================================================================
    # TEST 6: idempotent rebuild — no duplicates
    # ===================================================================
    print("\nTest 6: idempotent rebuild — no duplicates")
    result2 = build_manufacturing_plan(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
        cut_rule_set_id=ids1["cut_rule_set_id"],
    )
    plans_after = fake1.tables["app.run_manufacturing_plans"]
    contours_after = fake1.tables["app.run_manufacturing_contours"]
    _test("still 1 plan after rebuild", len(plans_after) == 1)
    _test("still 2 contours after rebuild", len(contours_after) == 2)
    _test("rebuild plans_created == 1", result2.get("plans_created") == 1)
    _test("rebuild contours_created == 2", result2.get("contours_created") == 2)

    # cut_order_index still deterministic
    cut_orders_after = sorted(c.get("cut_order_index", -1) for c in contours_after)
    _test("cut_order_index deterministic after rebuild", cut_orders_after == [0, 1])

    # ===================================================================
    # TEST 7: explicit cut_rule_set_id required
    # ===================================================================
    print("\nTest 7: explicit cut_rule_set_id required — missing raises error")
    fake7 = FakeSupabaseClient()
    ids7 = _seed_full(fake7)

    err7 = False
    try:
        build_manufacturing_plan(
            supabase=fake7,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids7["run_id"],
            cut_rule_set_id="",
        )
    except ManufacturingPlanBuilderError as exc:
        err7 = "cut_rule_set_id" in exc.detail
    _test("empty cut_rule_set_id raises error", err7)

    err7b = False
    try:
        build_manufacturing_plan(
            supabase=fake7,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids7["run_id"],
            cut_rule_set_id="   ",
        )
    except ManufacturingPlanBuilderError as exc:
        err7b = "cut_rule_set_id" in exc.detail
    _test("whitespace cut_rule_set_id raises error", err7b)

    # ===================================================================
    # TEST 8: snapshot without manufacturing selection -> error
    # ===================================================================
    print("\nTest 8: snapshot without manufacturing selection -> error")
    fake8 = FakeSupabaseClient()
    ids8 = _seed_full(fake8)
    # Override snapshot to have no selection
    fake8.tables["app.nesting_run_snapshots"][0]["manufacturing_manifest_jsonb"] = {
        "mode": "h2_e4_t1_snapshot_selection",
        "selection_present": False,
        "postprocess_selection_present": False,
    }
    err8 = False
    try:
        build_manufacturing_plan(
            supabase=fake8,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=ids8["run_id"],
            cut_rule_set_id=ids8["cut_rule_set_id"],
        )
    except ManufacturingPlanBuilderError as exc:
        err8 = "no manufacturing selection" in exc.detail
    _test("no manufacturing selection -> error", err8)

    # ===================================================================
    # TEST 9: run not owned by user -> error
    # ===================================================================
    print("\nTest 9: run not owned by user -> error")
    fake9 = FakeSupabaseClient()
    ids9 = _seed_full(fake9)
    err9 = False
    try:
        build_manufacturing_plan(
            supabase=fake9,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id="other-user-id",
            run_id=ids9["run_id"],
            cut_rule_set_id=ids9["cut_rule_set_id"],
        )
    except ManufacturingPlanBuilderError as exc:
        err9 = "not found" in exc.detail or "not owned" in exc.detail
    _test("wrong owner -> error", err9)

    # ===================================================================
    # Summary
    # ===================================================================
    total = passed + failed
    print(f"\n{'=' * 60}")
    if failed == 0:
        print(f"[PASS] smoke_h2_e4_t2_manufacturing_plan_builder: {passed}/{total} tests passed")
        return 0
    else:
        print(
            f"[FAIL] smoke_h2_e4_t2_manufacturing_plan_builder: {passed}/{total} passed, {failed} failed",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
