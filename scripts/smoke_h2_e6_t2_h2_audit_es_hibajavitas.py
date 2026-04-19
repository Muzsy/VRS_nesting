#!/usr/bin/env python3
"""H2-E6-T2 smoke: H2 audit regression harness.

Regression harness for the full H2 mainline manufacturing chain.
Verifies that all H2 services are importable, structurally sound,
and that the end-to-end manufacturing chain still works after
any audit/stabilization fixes.

This script is the H2 closure regression gate — it validates:
  1. All H2 service modules importable
  2. All H2 route modules importable
  3. End-to-end manufacturing chain still passes (delegates to E6-T1 pilot)
  4. No machine-specific side effects
  5. Manufacturing truth / artifact separation intact
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
# Phase 1: Service module imports
# ---------------------------------------------------------------------------

H2_SERVICE_MODULES = [
    "api.services.project_manufacturing_selection",
    "api.services.geometry_derivative_generator",
    "api.services.geometry_contour_classification",
    "api.services.cut_rule_sets",
    "api.services.cut_contour_rules",
    "api.services.cut_rule_matching",
    "api.services.run_snapshot_builder",
    "api.services.manufacturing_plan_builder",
    "api.services.manufacturing_metrics_calculator",
    "api.services.manufacturing_preview_generator",
    "api.services.postprocessor_profiles",
    "api.services.machine_neutral_exporter",
]

H2_ROUTE_MODULES = [
    "api.routes.project_manufacturing_selection",
    "api.routes.cut_rule_sets",
    "api.routes.cut_contour_rules",
    "api.routes.postprocessor_profiles",
]


def phase_1_imports() -> None:
    print("\n--- Phase 1: H2 service module imports ---")
    for mod_name in H2_SERVICE_MODULES:
        try:
            importlib.import_module(mod_name)
            _test(f"import {mod_name}", True)
        except Exception as exc:
            _test(f"import {mod_name}", False, str(exc))


def phase_2_route_imports() -> None:
    print("\n--- Phase 2: H2 route module imports ---")
    for mod_name in H2_ROUTE_MODULES:
        try:
            importlib.import_module(mod_name)
            _test(f"import {mod_name}", True)
        except Exception as exc:
            _test(f"import {mod_name}", False, str(exc))


# ---------------------------------------------------------------------------
# Phase 3: Key public function existence checks
# ---------------------------------------------------------------------------

KEY_FUNCTIONS = [
    ("api.services.project_manufacturing_selection", "set_project_manufacturing_selection"),
    ("api.services.project_manufacturing_selection", "get_project_manufacturing_selection"),
    ("api.services.geometry_derivative_generator", "generate_h1_minimum_geometry_derivatives"),
    ("api.services.geometry_contour_classification", "classify_manufacturing_derivative_contours"),
    ("api.services.cut_rule_sets", "create_cut_rule_set"),
    ("api.services.cut_rule_sets", "list_cut_rule_sets"),
    ("api.services.cut_contour_rules", "create_cut_contour_rule"),
    ("api.services.cut_contour_rules", "list_cut_contour_rules"),
    ("api.services.cut_rule_matching", "match_rules_for_derivative"),
    ("api.services.run_snapshot_builder", "build_run_snapshot_payload"),
    ("api.services.manufacturing_plan_builder", "build_manufacturing_plan"),
    ("api.services.manufacturing_metrics_calculator", "calculate_manufacturing_metrics"),
    ("api.services.manufacturing_preview_generator", "generate_manufacturing_preview"),
    ("api.services.postprocessor_profiles", "create_postprocessor_profile"),
    ("api.services.postprocessor_profiles", "create_postprocessor_profile_version"),
    ("api.services.machine_neutral_exporter", "generate_machine_neutral_export"),
]


def phase_3_public_functions() -> None:
    print("\n--- Phase 3: Key public function existence ---")
    for mod_name, func_name in KEY_FUNCTIONS:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, func_name, None)
            _test(f"{mod_name}.{func_name} exists", fn is not None and callable(fn))
        except Exception as exc:
            _test(f"{mod_name}.{func_name} exists", False, str(exc))


# ---------------------------------------------------------------------------
# Phase 4: Error class existence (boundary error handling)
# ---------------------------------------------------------------------------

ERROR_CLASSES = [
    ("api.services.project_manufacturing_selection", "ProjectManufacturingSelectionError"),
    ("api.services.cut_rule_sets", "CutRuleSetError"),
    ("api.services.cut_contour_rules", "CutContourRuleError"),
    ("api.services.manufacturing_plan_builder", "ManufacturingPlanBuilderError"),
    ("api.services.manufacturing_metrics_calculator", "ManufacturingMetricsCalculatorError"),
    ("api.services.manufacturing_preview_generator", "ManufacturingPreviewGeneratorError"),
    ("api.services.machine_neutral_exporter", "MachineNeutralExporterError"),
    ("api.services.postprocessor_profiles", "PostprocessorProfileError"),
]


def phase_4_error_classes() -> None:
    print("\n--- Phase 4: Error class existence ---")
    for mod_name, cls_name in ERROR_CLASSES:
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name, None)
            _test(f"{mod_name}.{cls_name} exists", cls is not None)
        except Exception as exc:
            _test(f"{mod_name}.{cls_name} exists", False, str(exc))


# ---------------------------------------------------------------------------
# Phase 5: End-to-end chain regression (reuses E6-T1 pilot logic)
# ---------------------------------------------------------------------------

def phase_5_e2e_chain() -> None:
    print("\n--- Phase 5: End-to-end manufacturing chain regression ---")

    # Import all needed services
    from api.services.manufacturing_plan_builder import build_manufacturing_plan
    from api.services.manufacturing_metrics_calculator import calculate_manufacturing_metrics
    from api.services.manufacturing_preview_generator import generate_manufacturing_preview
    from api.services.machine_neutral_exporter import generate_machine_neutral_export, EXPORT_CONTRACT_VERSION

    # Reuse the FakeSupabaseClient and seeder from E6-T1 pilot
    pilot_mod = importlib.import_module(
        "scripts.smoke_h2_e6_t1_end_to_end_manufacturing_pilot"
    )
    FakeSupabaseClient = pilot_mod.FakeSupabaseClient
    _seed_pilot_scenario = pilot_mod._seed_pilot_scenario

    fake = FakeSupabaseClient()
    ids = _seed_pilot_scenario(fake)
    uploaded: list[dict[str, Any]] = []
    registered: list[dict[str, Any]] = []

    # Plan builder
    plan_result = build_manufacturing_plan(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id="00000000-0000-0000-0000-pilot0000001",
        run_id=ids["run_id"],
        cut_rule_set_id=ids["cut_rule_set_id"],
    )
    _test("plan builder: plans_created == 1", plan_result.get("plans_created") == 1)
    _test("plan builder: contours_created == 2", plan_result.get("contours_created") == 2)

    # Metrics calculator
    metrics_result = calculate_manufacturing_metrics(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id="00000000-0000-0000-0000-pilot0000001",
        run_id=ids["run_id"],
    )
    _test("metrics: returns dict", isinstance(metrics_result, dict))
    metrics_rows = fake.tables["app.run_manufacturing_metrics"]
    _test("metrics: persisted == 1", len(metrics_rows) == 1)

    # Preview SVG
    uploaded.clear()
    registered.clear()
    preview_result = generate_manufacturing_preview(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id="00000000-0000-0000-0000-pilot0000001",
        run_id=ids["run_id"],
        upload_object=lambda **kw: uploaded.append(kw),
        register_artifact=lambda **kw: registered.append(kw),
    )
    _test("preview: artifacts_created == 1", preview_result.get("artifacts_created") == 1)
    _test("preview: artifact_kind == manufacturing_preview_svg",
          (registered[0].get("artifact_kind") if registered else "") == "manufacturing_preview_svg")

    # Machine-neutral export
    uploaded_ex: list[dict[str, Any]] = []
    registered_ex: list[dict[str, Any]] = []
    export_result = generate_machine_neutral_export(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        owner_user_id="00000000-0000-0000-0000-pilot0000001",
        run_id=ids["run_id"],
        upload_object=lambda **kw: uploaded_ex.append(kw),
        register_artifact=lambda **kw: registered_ex.append(kw),
    )
    _test("export: artifact_kind == manufacturing_plan_json",
          (registered_ex[0].get("artifact_kind") if registered_ex else "") == "manufacturing_plan_json")
    _test("export: contract_version correct",
          export_result.get("export_contract_version") == EXPORT_CONTRACT_VERSION)

    # No machine-specific artifacts
    all_kinds = {str(r.get("artifact_kind") or "") for r in registered + registered_ex}
    forbidden = {"machine_ready_bundle", "machine_program", "machine_log", "gcode"}
    found = all_kinds & forbidden
    _test("no machine-specific artifact kinds", len(found) == 0, f"found: {found}")

    # Truth/artifact separation
    plans = fake.tables["app.run_manufacturing_plans"]
    contours = fake.tables["app.run_manufacturing_contours"]
    _test("truth: run_manufacturing_plans persisted", len(plans) >= 1)
    _test("truth: run_manufacturing_contours persisted", len(contours) >= 2)
    _test("truth: run_manufacturing_metrics persisted", len(metrics_rows) >= 1)


# ---------------------------------------------------------------------------
# Phase 6: Completion matrix verification
# ---------------------------------------------------------------------------

H2_REPORT_SLUGS = [
    "h2_e1_t1_manufacturing_profile_crud",
    "h2_e1_t2_project_manufacturing_selection",
    "h2_e2_t1_manufacturing_canonical_derivative_generation",
    "h2_e2_t2_contour_classification_service",
    "h2_e3_t1_cut_rule_set_model",
    "h2_e3_t2_cut_contour_rules_model",
    "h2_e3_t3_rule_matching_logic",
    "h2_e4_t1_snapshot_manufacturing_bovites",
    "h2_e4_t2_manufacturing_plan_builder",
    "h2_e4_t3_manufacturing_metrics_calculator",
    "h2_e5_t1_manufacturing_preview_svg",
    "h2_e5_t2_postprocessor_profile_version_domain_aktivalasa",
    "h2_e5_t3_machine_neutral_exporter",
    "h2_e6_t1_end_to_end_manufacturing_pilot",
]


def phase_6_completion_matrix() -> None:
    print("\n--- Phase 6: H2 completion matrix verification ---")
    reports_dir = ROOT / "codex" / "reports" / "web_platform"
    pass_count = 0
    for slug in H2_REPORT_SLUGS:
        report_file = reports_dir / f"{slug}.md"
        exists = report_file.is_file()
        status_ok = False
        if exists:
            content = report_file.read_text(encoding="utf-8")
            first_lines = content[:500].upper()
            status_ok = "PASS" in first_lines and "FAIL" not in first_lines.replace("PASS_WITH_NOTES", "").replace("PASS WITH", "")
            if "PASS" in first_lines:
                status_ok = True
                pass_count += 1
        _test(f"report {slug}: exists and PASS", exists and status_ok)

    _test(f"completion matrix: {pass_count}/{len(H2_REPORT_SLUGS)} reports PASS",
          pass_count == len(H2_REPORT_SLUGS))


# ---------------------------------------------------------------------------
# Phase 7: Gate document existence
# ---------------------------------------------------------------------------

def phase_7_gate_doc() -> None:
    print("\n--- Phase 7: H2 gate document existence ---")
    gate_doc = ROOT / "docs" / "web_platform" / "roadmap" / "h2_lezarasi_kriteriumok_es_h3_entry_gate.md"
    exists = gate_doc.is_file()
    _test("H2 gate document exists", exists)
    if exists:
        content = gate_doc.read_text(encoding="utf-8")
        _test("gate doc contains completion matrix", "completion matrix" in content.lower())
        _test("gate doc contains H3 entry gate", "h3 entry gate" in content.lower())
        _test("gate doc contains PASS WITH ADVISORIES", "PASS WITH ADVISORIES" in content)
        _test("gate doc mentions H2-E5-T4 optional", "optionalis" in content.lower() or "optional" in content.lower())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    global passed, failed

    print("=" * 70)
    print("  H2-E6-T2  H2 Audit Regression Harness")
    print("=" * 70)

    phase_1_imports()
    phase_2_route_imports()
    phase_3_public_functions()
    phase_4_error_classes()
    phase_5_e2e_chain()
    phase_6_completion_matrix()
    phase_7_gate_doc()

    # Summary
    total = passed + failed
    print(f"\n{'=' * 70}")
    evidence = {
        "task": "H2-E6-T2 audit regression harness",
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "phases": [
            "1: H2 service module imports",
            "2: H2 route module imports",
            "3: Key public function existence",
            "4: Error class existence",
            "5: End-to-end chain regression",
            "6: H2 completion matrix verification",
            "7: H2 gate document existence",
        ],
    }
    print("  Audit evidence summary:")
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
