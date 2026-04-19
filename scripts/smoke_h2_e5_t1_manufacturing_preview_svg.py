#!/usr/bin/env python3
"""H2-E5-T1 smoke: manufacturing preview SVG — preview artifact generator."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.manufacturing_preview_generator import (  # noqa: E402
    generate_manufacturing_preview,
    ManufacturingPreviewGeneratorError,
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
# Fake Supabase client
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "app.nesting_runs": [],
            "app.run_manufacturing_plans": [],
            "app.run_manufacturing_contours": [],
            "app.run_layout_sheets": [],
            "app.geometry_derivatives": [],
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
# Upload/register fakes
# ---------------------------------------------------------------------------

_uploaded: list[dict[str, Any]] = []
_registered: list[dict[str, Any]] = []


def _fake_upload(**kwargs: Any) -> None:
    _uploaded.append(kwargs)


def _fake_register(**kwargs: Any) -> None:
    _registered.append(kwargs)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-000000000001"
PROJECT_ID = "00000000-0000-0000-0000-000000000002"


def _seed_full(fake: FakeSupabaseClient) -> dict[str, str]:
    """Seed a complete happy-path scenario with persisted manufacturing plan."""
    run_id = str(uuid4())
    plan_id = str(uuid4())
    sheet_id = str(uuid4())
    placement_id = str(uuid4())
    mfg_derivative_id = str(uuid4())

    # Run
    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })

    # Sheet
    fake.tables["app.run_layout_sheets"].append({
        "id": sheet_id,
        "run_id": run_id,
        "sheet_index": 0,
        "width_mm": 1000.0,
        "height_mm": 500.0,
    })

    # Persisted manufacturing plan
    fake.tables["app.run_manufacturing_plans"].append({
        "id": plan_id,
        "run_id": run_id,
        "sheet_id": sheet_id,
        "manufacturing_profile_version_id": str(uuid4()),
        "status": "generated",
        "summary_jsonb": {"builder_scope": "h2_e4_t2", "placement_count": 1},
    })

    # Manufacturing derivative with contour geometry
    fake.tables["app.geometry_derivatives"].append({
        "id": mfg_derivative_id,
        "derivative_kind": "manufacturing_canonical",
        "derivative_jsonb": {
            "derivative_kind": "manufacturing_canonical",
            "format_version": "manufacturing_canonical.v1",
            "units": "mm",
            "contours": [
                {
                    "contour_index": 0,
                    "contour_role": "outer",
                    "winding": "ccw",
                    "points": [
                        [10.0, 10.0], [90.0, 10.0], [90.0, 90.0], [10.0, 90.0],
                    ],
                },
                {
                    "contour_index": 1,
                    "contour_role": "hole",
                    "winding": "cw",
                    "points": [
                        [30.0, 30.0], [70.0, 30.0], [70.0, 70.0], [30.0, 70.0],
                    ],
                },
            ],
            "bbox": {"min_x": 10.0, "min_y": 10.0, "max_x": 90.0, "max_y": 90.0, "width": 80.0, "height": 80.0},
        },
    })

    # Manufacturing contours (outer + inner)
    fake.tables["app.run_manufacturing_contours"].extend([
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "placement_id": placement_id,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_index": 0,
            "contour_kind": "outer",
            "feature_class": "default",
            "entry_point_jsonb": {"x": 10.0, "y": 10.0, "rotation_deg": 0.0, "source": "placement_transform"},
            "lead_in_jsonb": {"type": "line", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "line", "source": "matched_rule"},
            "cut_order_index": 0,
        },
        {
            "id": str(uuid4()),
            "manufacturing_plan_id": plan_id,
            "placement_id": placement_id,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_index": 1,
            "contour_kind": "inner",
            "feature_class": "default",
            "entry_point_jsonb": {"x": 30.0, "y": 30.0, "rotation_deg": 0.0, "source": "placement_transform"},
            "lead_in_jsonb": {"type": "arc", "source": "matched_rule"},
            "lead_out_jsonb": {"type": "none", "source": "matched_rule"},
            "cut_order_index": 1,
        },
    ])

    return {
        "run_id": run_id,
        "plan_id": plan_id,
        "sheet_id": sheet_id,
        "mfg_derivative_id": mfg_derivative_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed, _uploaded, _registered

    # ===================================================================
    # TEST 1: valid persisted plan -> preview artifact created
    # ===================================================================
    print("Test 1: valid persisted plan -> preview artifact created")
    fake1 = FakeSupabaseClient()
    ids1 = _seed_full(fake1)
    _uploaded = []
    _registered = []

    result1 = generate_manufacturing_preview(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
        upload_object=_fake_upload,
        register_artifact=_fake_register,
    )
    _test("result is dict", isinstance(result1, dict))
    _test("run_id correct", result1.get("run_id") == ids1["run_id"])
    _test("artifacts_created == 1", result1.get("artifacts_created") == 1)
    _test("1 upload", len(_uploaded) == 1)
    _test("1 register", len(_registered) == 1)

    arts = result1.get("artifacts") or []
    _test("artifact has sheet_index 0", len(arts) == 1 and arts[0].get("sheet_index") == 0)
    _test("filename matches pattern", "manufacturing_preview_sheet_001.svg" in (arts[0].get("filename") or ""))
    _test("storage_path has manufacturing_preview_svg", "manufacturing_preview_svg/" in (arts[0].get("storage_path") or ""))
    _test("content_sha256 present", bool(arts[0].get("content_sha256")))
    _test("size_bytes > 0", (arts[0].get("size_bytes") or 0) > 0)

    # ===================================================================
    # TEST 2: preview SVG contains manufacturing meta (entry/lead/cut-order)
    # ===================================================================
    print("\nTest 2: preview SVG has manufacturing meta-information")
    uploaded_payload = _uploaded[0].get("payload", b"")
    svg_text = uploaded_payload.decode("utf-8") if isinstance(uploaded_payload, bytes) else str(uploaded_payload)
    _test("SVG contains data-preview-scope", 'data-preview-scope="h2_e5_t1"' in svg_text)
    _test("SVG contains entry-marker", 'data-role="entry-marker"' in svg_text)
    _test("SVG contains cut-order label", 'data-role="cut-order-label"' in svg_text)
    _test("SVG contains lead-in", 'data-role="lead-in"' in svg_text)
    _test("SVG contains data-cut-order", 'data-cut-order="0"' in svg_text)
    _test("SVG contains data-cut-order 1", 'data-cut-order="1"' in svg_text)

    # ===================================================================
    # TEST 3: render uses manufacturing_canonical contour geometry
    # ===================================================================
    print("\nTest 3: render uses manufacturing_canonical geometry")
    _test("SVG contains outer contour path (10.0)", "10.000000" in svg_text)
    _test("SVG contains outer contour path (90.0)", "90.000000" in svg_text)
    _test("SVG contains inner contour points (30.0)", "30.000000" in svg_text)
    _test("SVG contains inner contour points (70.0)", "70.000000" in svg_text)

    # ===================================================================
    # TEST 4: outer/inner contour visual distinction present
    # ===================================================================
    print("\nTest 4: outer/inner contour distinction")
    _test("SVG has data-contour-kind=outer", 'data-contour-kind="outer"' in svg_text)
    _test("SVG has data-contour-kind=inner", 'data-contour-kind="inner"' in svg_text)

    # ===================================================================
    # TEST 5: idempotent rerun does not duplicate artifacts
    # ===================================================================
    print("\nTest 5: idempotent rerun")
    _uploaded = []
    _registered = []

    result2 = generate_manufacturing_preview(
        supabase=fake1,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids1["run_id"],
        upload_object=_fake_upload,
        register_artifact=_fake_register,
    )
    _test("second run also succeeds", result2.get("artifacts_created") == 1)
    # Check no duplicated artifacts remain (delete + re-insert)
    _test("upload called again", len(_uploaded) == 1)
    _test("register called again", len(_registered) == 1)

    # Check write log for delete before insert
    delete_ops = [w for w in fake1.write_log if w.get("op") == "delete" and w.get("table") == "app.run_artifacts"]
    _test("idempotent delete happened", len(delete_ops) >= 2,
          f"got {len(delete_ops)} delete ops")

    # ===================================================================
    # TEST 6: generator does not write to earlier truth tables
    # ===================================================================
    print("\nTest 6: no write to earlier truth tables")
    forbidden_tables = {
        "app.run_manufacturing_plans",
        "app.run_manufacturing_contours",
        "app.run_manufacturing_metrics",
        "app.geometry_contour_classes",
        "app.cut_contour_rules",
    }
    violated = set()
    for w in fake1.write_log:
        tbl = w.get("table", "")
        if tbl in forbidden_tables:
            violated.add(tbl)
    _test("no write to forbidden truth tables", len(violated) == 0,
          f"violated: {violated}")

    # ===================================================================
    # TEST 7: no export/postprocess artifact created
    # ===================================================================
    print("\nTest 7: no export/postprocess artifact")
    for reg in _registered:
        ak = str(reg.get("artifact_kind") or "")
        _test(f"artifact_kind is {ak}", ak == "manufacturing_preview_svg",
              f"unexpected artifact_kind: {ak}")

    # ===================================================================
    # TEST 8: error on missing manufacturing_canonical derivative
    # ===================================================================
    print("\nTest 8: error on missing derivative")
    fake8 = FakeSupabaseClient()
    run_id_8 = str(uuid4())
    plan_id_8 = str(uuid4())
    sheet_id_8 = str(uuid4())
    bad_derivative_id = str(uuid4())

    fake8.tables["app.nesting_runs"].append({
        "id": run_id_8,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })
    fake8.tables["app.run_layout_sheets"].append({
        "id": sheet_id_8,
        "run_id": run_id_8,
        "sheet_index": 0,
        "width_mm": 500.0,
        "height_mm": 300.0,
    })
    fake8.tables["app.run_manufacturing_plans"].append({
        "id": plan_id_8,
        "run_id": run_id_8,
        "sheet_id": sheet_id_8,
        "status": "generated",
        "summary_jsonb": {},
    })
    fake8.tables["app.run_manufacturing_contours"].append({
        "id": str(uuid4()),
        "manufacturing_plan_id": plan_id_8,
        "placement_id": str(uuid4()),
        "geometry_derivative_id": bad_derivative_id,
        "contour_index": 0,
        "contour_kind": "outer",
        "feature_class": "default",
        "entry_point_jsonb": {"x": 0, "y": 0},
        "lead_in_jsonb": {"type": "none"},
        "lead_out_jsonb": {"type": "none"},
        "cut_order_index": 0,
    })

    _uploaded_8: list[dict[str, Any]] = []
    _registered_8: list[dict[str, Any]] = []
    got_error = False
    try:
        generate_manufacturing_preview(
            supabase=fake8,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=run_id_8,
            upload_object=lambda **kw: _uploaded_8.append(kw),
            register_artifact=lambda **kw: _registered_8.append(kw),
        )
    except ManufacturingPreviewGeneratorError as exc:
        got_error = True
        _test("error mentions derivative", "derivative" in exc.detail.lower() or "not found" in exc.detail.lower())

    _test("ManufacturingPreviewGeneratorError raised for missing derivative", got_error)

    # ===================================================================
    # TEST 9: error when wrong derivative kind
    # ===================================================================
    print("\nTest 9: error on wrong derivative kind")
    fake9 = FakeSupabaseClient()
    run_id_9 = str(uuid4())
    plan_id_9 = str(uuid4())
    sheet_id_9 = str(uuid4())
    wrong_derivative_id = str(uuid4())

    fake9.tables["app.nesting_runs"].append({
        "id": run_id_9,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })
    fake9.tables["app.run_layout_sheets"].append({
        "id": sheet_id_9,
        "run_id": run_id_9,
        "sheet_index": 0,
        "width_mm": 500.0,
        "height_mm": 300.0,
    })
    fake9.tables["app.run_manufacturing_plans"].append({
        "id": plan_id_9,
        "run_id": run_id_9,
        "sheet_id": sheet_id_9,
        "status": "generated",
        "summary_jsonb": {},
    })
    fake9.tables["app.run_manufacturing_contours"].append({
        "id": str(uuid4()),
        "manufacturing_plan_id": plan_id_9,
        "placement_id": str(uuid4()),
        "geometry_derivative_id": wrong_derivative_id,
        "contour_index": 0,
        "contour_kind": "outer",
        "feature_class": "default",
        "entry_point_jsonb": {"x": 0, "y": 0},
        "lead_in_jsonb": {"type": "none"},
        "lead_out_jsonb": {"type": "none"},
        "cut_order_index": 0,
    })
    # Wrong derivative kind
    fake9.tables["app.geometry_derivatives"].append({
        "id": wrong_derivative_id,
        "derivative_kind": "nesting_canonical",
        "derivative_jsonb": {},
    })

    got_error_9 = False
    try:
        generate_manufacturing_preview(
            supabase=fake9,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=run_id_9,
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except ManufacturingPreviewGeneratorError:
        got_error_9 = True
    _test("error raised for wrong derivative kind", got_error_9)

    # ===================================================================
    # TEST 10: error when no manufacturing plans
    # ===================================================================
    print("\nTest 10: error when no manufacturing plans")
    fake10 = FakeSupabaseClient()
    run_id_10 = str(uuid4())
    fake10.tables["app.nesting_runs"].append({
        "id": run_id_10,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })

    got_error_10 = False
    try:
        generate_manufacturing_preview(
            supabase=fake10,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=run_id_10,
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except ManufacturingPreviewGeneratorError:
        got_error_10 = True
    _test("error raised for missing manufacturing plans", got_error_10)

    # ===================================================================
    # TEST 11: register metadata contains required fields
    # ===================================================================
    print("\nTest 11: artifact metadata policy")
    if _registered:
        meta = _registered[0].get("metadata_json") or {}
        _test("metadata has filename", "filename" in meta)
        _test("metadata has sheet_index", "sheet_index" in meta)
        _test("metadata has size_bytes", "size_bytes" in meta)
        _test("metadata has content_sha256", "content_sha256" in meta)
        _test("metadata has legacy_artifact_type", meta.get("legacy_artifact_type") == "manufacturing_preview_svg")
        _test("metadata has preview_scope", meta.get("preview_scope") == "h2_e5_t1")

    # ===================================================================
    # TEST 12: upload bucket is run-artifacts
    # ===================================================================
    print("\nTest 12: bucket is run-artifacts")
    if _uploaded:
        _test("bucket is run-artifacts", _uploaded[0].get("bucket") == "run-artifacts")

    # ===================================================================
    # Summary
    # ===================================================================
    print(f"\n{'=' * 60}")
    total = passed + failed
    print(f"  TOTAL: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
    if failed:
        print("  STATUS: FAIL")
    else:
        print("  STATUS: PASS")
    print(f"{'=' * 60}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
