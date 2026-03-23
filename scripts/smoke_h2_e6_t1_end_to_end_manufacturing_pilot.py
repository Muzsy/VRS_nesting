#!/usr/bin/env python3
"""H2-E6-T1 smoke: end-to-end manufacturing pilot.

Single seeded scenario proving the H2 mainline chain:
  manufacturing/postprocess snapshot
  -> manufacturing plan builder
  -> manufacturing metrics calculator
  -> manufacturing preview SVG
  -> machine-neutral export artifact

This is NOT a shell runner that calls earlier smokes sequentially.
Instead it seeds ONE consistent scenario and drives all H2 services
in order, then verifies the full truth + artifact evidence.
"""

from __future__ import annotations

import json
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
from api.services.manufacturing_metrics_calculator import (  # noqa: E402
    calculate_manufacturing_metrics,
    ManufacturingMetricsCalculatorError,
)
from api.services.manufacturing_preview_generator import (  # noqa: E402
    generate_manufacturing_preview,
    ManufacturingPreviewGeneratorError,
)
from api.services.machine_neutral_exporter import (  # noqa: E402
    generate_machine_neutral_export,
    MachineNeutralExporterError,
    EXPORT_CONTRACT_VERSION,
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
# Unified FakeSupabaseClient (supports all H2 services)
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    """In-memory Supabase stub covering all tables needed by the H2 chain."""

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
# Upload/register fakes
# ---------------------------------------------------------------------------

_uploaded: list[dict[str, Any]] = []
_registered: list[dict[str, Any]] = []


def _fake_upload(**kwargs: Any) -> None:
    _uploaded.append(kwargs)


def _fake_register(**kwargs: Any) -> None:
    _registered.append(kwargs)


# ---------------------------------------------------------------------------
# Seeded H2 pilot scenario
# ---------------------------------------------------------------------------

OWNER_ID = "00000000-0000-0000-0000-pilot0000001"
PROJECT_ID = "00000000-0000-0000-0000-pilot0000002"
MFG_PROFILE_VERSION_ID = "00000000-0000-0000-0000-pilot0000003"
PP_VERSION_ID = "00000000-0000-0000-0000-pilot0000004"


def _seed_pilot_scenario(fake: FakeSupabaseClient) -> dict[str, str]:
    """Seed ONE consistent H2 pilot scenario.

    Fixture: 1 project, 1 run, 1 sheet (3000x1500 mm),
    1 placement with 1 outer + 1 inner contour,
    active manufacturing profile version,
    active postprocessor profile version (metadata-only),
    cut rule set with outer + inner rules.
    """
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

    # ---- Run ----
    fake.tables["app.nesting_runs"].append({
        "id": run_id,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })

    # ---- Snapshot with manufacturing + postprocessor selection ----
    mfg_manifest: dict[str, Any] = {
        "mode": "h2_e5_t2_snapshot_selection",
        "project_id": PROJECT_ID,
        "selection_present": True,
        "selected_at": "2026-03-23T00:00:00Z",
        "selected_by": OWNER_ID,
        "active_manufacturing_profile_version_id": MFG_PROFILE_VERSION_ID,
        "manufacturing_profile_version": {
            "manufacturing_profile_id": str(uuid4()),
            "version_no": 1,
            "lifecycle": "approved",
            "is_active": True,
            "machine_code": "PILOT_LASER",
            "material_code": "ST37",
            "thickness_mm": 6.0,
            "kerf_mm": 0.3,
            "config_jsonb": {},
        },
        "postprocess_selection_present": True,
        "postprocessor_profile_version": {
            "active_postprocessor_profile_version_id": PP_VERSION_ID,
            "postprocessor_profile_id": str(uuid4()),
            "version_no": 1,
            "lifecycle": "approved",
            "is_active": True,
            "adapter_key": "generic",
            "output_format": "json",
            "schema_version": "v1",
        },
    }

    fake.tables["app.nesting_run_snapshots"].append({
        "id": snapshot_id,
        "run_id": run_id,
        "manufacturing_manifest_jsonb": mfg_manifest,
        "includes_manufacturing": True,
        "includes_postprocess": True,
    })

    # ---- Projection: 1 sheet, 1 placement ----
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
        "transform_jsonb": {"x": 50.0, "y": 75.0, "rotation_deg": 0.0},
        "bbox_jsonb": {"min_x": 50.0, "min_y": 75.0, "max_x": 250.0, "max_y": 175.0, "width": 200.0, "height": 100.0},
        "metadata_jsonb": {},
    })

    # ---- Part revision with manufacturing derivative ----
    fake.tables["app.part_revisions"].append({
        "id": part_revision_id,
        "selected_manufacturing_derivative_id": mfg_derivative_id,
    })

    # ---- Manufacturing canonical derivative (outer rect + inner hole) ----
    fake.tables["app.geometry_derivatives"].append({
        "id": mfg_derivative_id,
        "geometry_revision_id": geo_rev_id,
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
                        [0.0, 0.0], [200.0, 0.0], [200.0, 100.0], [0.0, 100.0],
                    ],
                },
                {
                    "contour_index": 1,
                    "contour_role": "hole",
                    "winding": "cw",
                    "points": [
                        [40.0, 20.0], [160.0, 20.0], [160.0, 80.0], [40.0, 80.0],
                    ],
                },
            ],
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 200.0, "max_y": 100.0, "width": 200.0, "height": 100.0},
        },
    })

    # ---- Contour classification ----
    fake.tables["app.geometry_contour_classes"].extend([
        {
            "id": contour_class_id_0,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_index": 0,
            "contour_kind": "outer",
            "feature_class": "default",
            "is_closed": True,
            "area_mm2": 20000.0,
            "perimeter_mm": 600.0,
        },
        {
            "id": contour_class_id_1,
            "geometry_derivative_id": mfg_derivative_id,
            "contour_index": 1,
            "contour_kind": "inner",
            "feature_class": "default",
            "is_closed": True,
            "area_mm2": 7200.0,
            "perimeter_mm": 360.0,
        },
    ])

    # ---- Cut rule set + rules ----
    fake.tables["app.cut_rule_sets"].append({
        "id": cut_rule_set_id,
        "owner_user_id": OWNER_ID,
        "name": "Pilot H2 Rules",
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
            "pierce_count": 1,
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
            "pierce_count": 1,
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
        "mfg_profile_version_id": MFG_PROFILE_VERSION_ID,
        "rule_outer_id": rule_outer_id,
        "rule_inner_id": rule_inner_id,
        "contour_class_id_0": contour_class_id_0,
        "contour_class_id_1": contour_class_id_1,
    }


# ---------------------------------------------------------------------------
# Main pilot
# ---------------------------------------------------------------------------


def main() -> int:
    global passed, failed, _uploaded, _registered

    print("=" * 70)
    print("  H2-E6-T1  End-to-end Manufacturing Pilot")
    print("=" * 70)

    # ===================================================================
    # PHASE 1: Seed common H2 pilot fixture
    # ===================================================================
    print("\n--- Phase 1: Seed pilot fixture ---")
    fake = FakeSupabaseClient()
    ids = _seed_pilot_scenario(fake)
    _uploaded = []
    _registered = []

    _test("fixture seeded: run exists", len(fake.tables["app.nesting_runs"]) == 1)
    _test("fixture seeded: snapshot exists", len(fake.tables["app.nesting_run_snapshots"]) == 1)
    _test("fixture seeded: 1 sheet", len(fake.tables["app.run_layout_sheets"]) == 1)
    _test("fixture seeded: 1 placement", len(fake.tables["app.run_layout_placements"]) == 1)
    _test("fixture seeded: manufacturing derivative", len(fake.tables["app.geometry_derivatives"]) == 1)
    _test("fixture seeded: 2 contour classes", len(fake.tables["app.geometry_contour_classes"]) == 2)
    _test("fixture seeded: cut rule set + 2 rules",
          len(fake.tables["app.cut_rule_sets"]) == 1 and len(fake.tables["app.cut_contour_rules"]) == 2)

    # ===================================================================
    # PHASE 2: Manufacturing plan builder
    # ===================================================================
    print("\n--- Phase 2: Manufacturing plan builder ---")
    plan_result = build_manufacturing_plan(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids["run_id"],
        cut_rule_set_id=ids["cut_rule_set_id"],
    )
    _test("plan builder returns dict", isinstance(plan_result, dict))
    _test("plans_created == 1", plan_result.get("plans_created") == 1)
    _test("contours_created == 2", plan_result.get("contours_created") == 2)

    plans = fake.tables["app.run_manufacturing_plans"]
    contours = fake.tables["app.run_manufacturing_contours"]
    _test("persisted run_manufacturing_plans == 1", len(plans) == 1)
    _test("persisted run_manufacturing_contours == 2", len(contours) == 2)

    outer_c = next((c for c in contours if c.get("contour_kind") == "outer"), None)
    inner_c = next((c for c in contours if c.get("contour_kind") == "inner"), None)
    _test("outer contour persisted", outer_c is not None)
    _test("inner contour persisted", inner_c is not None)
    if outer_c:
        _test("outer.matched_rule_id correct", outer_c.get("matched_rule_id") == ids["rule_outer_id"])
        _test("outer.contour_class_id set", outer_c.get("contour_class_id") == ids["contour_class_id_0"])
        _test("outer.entry_point_jsonb is dict", isinstance(outer_c.get("entry_point_jsonb"), dict))
        _test("outer.lead_in_jsonb is dict", isinstance(outer_c.get("lead_in_jsonb"), dict))
    if inner_c:
        _test("inner.matched_rule_id correct", inner_c.get("matched_rule_id") == ids["rule_inner_id"])
        _test("inner.contour_class_id set", inner_c.get("contour_class_id") == ids["contour_class_id_1"])

    # ===================================================================
    # PHASE 3: Manufacturing metrics calculator
    # ===================================================================
    print("\n--- Phase 3: Manufacturing metrics calculator ---")
    metrics_result = calculate_manufacturing_metrics(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids["run_id"],
    )
    _test("metrics returns dict", isinstance(metrics_result, dict))

    metrics_rows = fake.tables["app.run_manufacturing_metrics"]
    _test("persisted run_manufacturing_metrics == 1", len(metrics_rows) == 1)

    mrow = metrics_rows[0]
    _test("metrics.pierce_count >= 0", (mrow.get("pierce_count") or 0) >= 0)
    _test("metrics.outer_contour_count == 1", mrow.get("outer_contour_count") == 1)
    _test("metrics.inner_contour_count == 1", mrow.get("inner_contour_count") == 1)
    _test("metrics.estimated_cut_length_mm > 0", (mrow.get("estimated_cut_length_mm") or 0) > 0)
    _test("metrics.estimated_process_time_s > 0", (mrow.get("estimated_process_time_s") or 0) > 0)
    _test("metrics.metrics_jsonb is dict", isinstance(mrow.get("metrics_jsonb"), dict))

    # ===================================================================
    # PHASE 4: Manufacturing preview SVG
    # ===================================================================
    print("\n--- Phase 4: Manufacturing preview SVG ---")
    _uploaded = []
    _registered = []

    preview_result = generate_manufacturing_preview(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids["run_id"],
        upload_object=_fake_upload,
        register_artifact=_fake_register,
    )
    _test("preview returns dict", isinstance(preview_result, dict))
    _test("preview artifacts_created == 1", preview_result.get("artifacts_created") == 1)
    _test("preview upload called", len(_uploaded) == 1)
    _test("preview register called", len(_registered) == 1)

    preview_reg = _registered[0] if _registered else {}
    _test("preview artifact_kind == manufacturing_preview_svg",
          preview_reg.get("artifact_kind") == "manufacturing_preview_svg")

    svg_bytes = _uploaded[0].get("payload", b"") if _uploaded else b""
    svg_text = svg_bytes.decode("utf-8") if isinstance(svg_bytes, bytes) else ""
    _test("SVG contains data-preview-scope", 'data-preview-scope="h2_e5_t1"' in svg_text)
    _test("SVG contains outer contour", 'data-contour-kind="outer"' in svg_text)
    _test("SVG contains inner contour", 'data-contour-kind="inner"' in svg_text)
    _test("SVG contains entry marker", 'data-role="entry-marker"' in svg_text)

    # ===================================================================
    # PHASE 5: Machine-neutral export
    # ===================================================================
    print("\n--- Phase 5: Machine-neutral export ---")
    _uploaded_export: list[dict[str, Any]] = []
    _registered_export: list[dict[str, Any]] = []

    export_result = generate_machine_neutral_export(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id=OWNER_ID,
        run_id=ids["run_id"],
        upload_object=lambda **kw: _uploaded_export.append(kw),
        register_artifact=lambda **kw: _registered_export.append(kw),
    )
    _test("export returns dict", isinstance(export_result, dict))
    _test("export filename is out/manufacturing_plan.json",
          export_result.get("filename") == "out/manufacturing_plan.json")
    _test("export contract version correct",
          export_result.get("export_contract_version") == EXPORT_CONTRACT_VERSION)
    _test("export upload called", len(_uploaded_export) == 1)
    _test("export register called", len(_registered_export) == 1)

    export_reg = _registered_export[0] if _registered_export else {}
    _test("export artifact_kind == manufacturing_plan_json",
          export_reg.get("artifact_kind") == "manufacturing_plan_json")

    export_bytes = _uploaded_export[0].get("payload", b"") if _uploaded_export else b""
    export_json = json.loads(export_bytes) if export_bytes else {}
    _test("export payload has sheets", isinstance(export_json.get("sheets"), list))
    _test("export payload sheets count == 1", len(export_json.get("sheets") or []) == 1)
    _test("export payload has manufacturing_metrics", "manufacturing_metrics" in export_json)
    _test("export payload has postprocessor_selection", "postprocessor_selection" in export_json)

    # ===================================================================
    # PHASE 6: Artifact evidence — full artifact list
    # ===================================================================
    print("\n--- Phase 6: Artifact evidence ---")
    all_artifact_kinds = set()
    all_registered = list(_registered) + list(_registered_export)
    for reg in all_registered:
        all_artifact_kinds.add(str(reg.get("artifact_kind") or ""))

    _test("manufacturing_preview_svg in artifact list",
          "manufacturing_preview_svg" in all_artifact_kinds)
    _test("manufacturing_plan_json in artifact list",
          "manufacturing_plan_json" in all_artifact_kinds)

    # ===================================================================
    # PHASE 7: No machine-specific side effects
    # ===================================================================
    print("\n--- Phase 7: No machine-specific side effects ---")
    forbidden_artifact_kinds = {"machine_ready_bundle", "machine_program", "machine_log", "gcode"}
    found_forbidden = all_artifact_kinds & forbidden_artifact_kinds
    _test("no machine-specific artifact kinds", len(found_forbidden) == 0,
          f"found: {found_forbidden}")

    export_text = export_bytes.decode("utf-8") if isinstance(export_bytes, bytes) else ""
    _test("no machine_ready_bundle in export payload", "machine_ready_bundle" not in export_text)
    _test("no gcode in export payload", "gcode" not in export_text.lower())
    _test("no machine_program in export payload", "machine_program" not in export_text)

    # Postprocessor metadata stays metadata-only
    pp_sel = export_json.get("postprocessor_selection") or {}
    _test("pp metadata has adapter_key", pp_sel.get("adapter_key") == "generic")
    _test("pp metadata has output_format", pp_sel.get("output_format") == "json")

    # ===================================================================
    # PHASE 8: No writes to forbidden truth tables
    # ===================================================================
    print("\n--- Phase 8: No writes to forbidden truth tables ---")
    forbidden_write_tables = {
        "app.geometry_contour_classes",
        "app.cut_contour_rules",
        "app.cut_rule_sets",
        "app.nesting_runs",
        "app.nesting_run_snapshots",
        "app.run_layout_sheets",
        "app.run_layout_placements",
        "app.part_revisions",
        "app.geometry_derivatives",
        "app.project_manufacturing_selection",
        "app.postprocessor_profile_versions",
    }
    violated = set()
    for w in fake.write_log:
        tbl = w.get("table", "")
        if tbl in forbidden_write_tables:
            violated.add(tbl)
    _test("no writes to upstream truth tables", len(violated) == 0,
          f"violated: {violated}")

    # ===================================================================
    # PHASE 9: Boundary error handling
    # ===================================================================
    print("\n--- Phase 9: Boundary error handling ---")

    # 9a: plan builder with wrong owner
    fake_err = FakeSupabaseClient()
    ids_err = _seed_pilot_scenario(fake_err)
    got_owner_err = False
    try:
        build_manufacturing_plan(
            supabase=fake_err,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id="wrong-owner",
            run_id=ids_err["run_id"],
            cut_rule_set_id=ids_err["cut_rule_set_id"],
        )
    except ManufacturingPlanBuilderError as exc:
        got_owner_err = "not found" in exc.detail.lower() or "not owned" in exc.detail.lower()
    _test("plan builder: wrong owner -> boundary error", got_owner_err)

    # 9b: metrics with no plans
    fake_no_plan = FakeSupabaseClient()
    no_plan_run_id = str(uuid4())
    fake_no_plan.tables["app.nesting_runs"].append({
        "id": no_plan_run_id,
        "owner_user_id": OWNER_ID,
        "project_id": PROJECT_ID,
        "status": "succeeded",
    })
    got_no_plan_err = False
    try:
        calculate_manufacturing_metrics(
            supabase=fake_no_plan,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id=OWNER_ID,
            run_id=no_plan_run_id,
        )
    except ManufacturingMetricsCalculatorError as exc:
        got_no_plan_err = "plan" in exc.detail.lower()
    _test("metrics: no plans -> boundary error", got_no_plan_err)

    # 9c: preview with wrong owner
    got_preview_err = False
    try:
        generate_manufacturing_preview(
            supabase=fake_err,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id="wrong-owner",
            run_id=ids_err["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except ManufacturingPreviewGeneratorError as exc:
        got_preview_err = "not found" in exc.detail.lower() or "not owned" in exc.detail.lower()
    _test("preview: wrong owner -> boundary error", got_preview_err)

    # 9d: export with wrong owner
    got_export_err = False
    try:
        generate_machine_neutral_export(
            supabase=fake_err,  # type: ignore[arg-type]
            access_token="tok",
            owner_user_id="wrong-owner",
            run_id=ids_err["run_id"],
            upload_object=lambda **kw: None,
            register_artifact=lambda **kw: None,
        )
    except MachineNeutralExporterError as exc:
        got_export_err = "not found" in exc.detail.lower() or "not owned" in exc.detail.lower()
    _test("export: wrong owner -> boundary error", got_export_err)

    # ===================================================================
    # PHASE 10: Summary
    # ===================================================================
    print(f"\n{'=' * 70}")
    total = passed + failed
    evidence = {
        "pilot_fixture": "1 project, 1 run, 1 sheet (3000x1500), 1 placement, 1 outer + 1 inner contour",
        "h2_boundaries_tested": [
            "manufacturing/postprocess snapshot truth",
            "manufacturing plan builder (run_manufacturing_plans + run_manufacturing_contours)",
            "manufacturing metrics calculator (run_manufacturing_metrics)",
            "manufacturing preview SVG (manufacturing_preview_svg artifact)",
            "machine-neutral exporter (manufacturing_plan_json artifact)",
        ],
        "persisted_truth": {
            "run_manufacturing_plans": len(fake.tables["app.run_manufacturing_plans"]),
            "run_manufacturing_contours": len(fake.tables["app.run_manufacturing_contours"]),
            "run_manufacturing_metrics": len(fake.tables["app.run_manufacturing_metrics"]),
        },
        "artifacts": sorted(all_artifact_kinds),
        "machine_specific_artifacts": sorted(found_forbidden),
        "forbidden_truth_writes": sorted(violated),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
    }
    print("  Pilot evidence summary:")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"\n  TOTAL: {total}  |  PASSED: {passed}  |  FAILED: {failed}")
    if failed:
        print("  STATUS: FAIL")
    else:
        print("  STATUS: PASS")
    print(f"{'=' * 70}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
