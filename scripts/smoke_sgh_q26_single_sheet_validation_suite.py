#!/usr/bin/env python3
"""Static gate for SGH-Q26 single-sheet Sparrow validation suite.

This smoke is intentionally benchmark-free. It verifies that the revised Q26 tests
exist, are single-sheet-only, target the native sparrow_cde+CDE path, assert the
right diagnostics, and include a concrete LV8-derived 40-80 instance one-sheet
validation without smuggling in first-sheet-191/full-276/multisheet acceptance.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "rust/vrs_solver/tests/sparrow_single_sheet_validation.rs"
FIX_DIR = ROOT / "rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation"
LV8_SMOKE = ROOT / "scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py"
LV8_MANIFEST = FIX_DIR / "lv8_derived_subset_manifest.json"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md"

PASS = 0
FAIL = 0
WARN = 0

ALLOWED_PREFIXES = (
    "rust/vrs_solver/tests/sparrow_single_sheet_validation.rs",
    "rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/",
    # SGH-Q26 LV8-derived gate fixture: normalized (CUT_OUTER/CUT_INNER) LV8 parts,
    # committed so the LV8-derived single-sheet smoke is reproducible. Authorized
    # as the repo-native fixture required by the LV8-derived validation.
    "samples/real_work_dxf/0014-01H/lv8jav_normalized/",
    "README_SGH_Q26_SINGLE_SHEET_SPARROW_VALIDATION_SUITE_REVISED_PACKAGE.md",
    "canvases/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md",
    "codex/codex_checklist/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md",
    "codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q26_single_sheet_sparrow_validation_suite.yaml",
    "codex/prompts/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite/",
    "codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md",
    "codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.verify.log",
    "scripts/smoke_sgh_q26_single_sheet_validation_suite.py",
    "scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py",
)

REQUIRED_TESTS = [
    "q26_single_sheet_tiny_rectangles_all_placed",
    "q26_single_sheet_requires_90_degree_rotation_all_placed",
    "q26_single_sheet_strict_cde_irregular_l_shape_mix_all_placed",
    "q26_single_sheet_medium_rect_mix_all_placed",
    "q26_single_sheet_medium_mixed_rotations_all_placed",
    "q26_single_sheet_serious_synthetic_40_to_80_instances_all_placed",
    "q26_single_sheet_deterministic_same_seed_same_output",
    "q26_single_sheet_negative_overcapacity_reports_partial_with_diagnostics",
]

REPORT_HEADERS = [
    "SGH-Q26_STATUS",
    "PRE_TASK_GIT_STATUS",
    "PRE_TASK_DIRTY_FILES",
    "PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES",
    "TASK_CHANGED_FILES",
    "OUT_OF_SCOPE_NEW_CHANGES",
    "VALIDATION_LEVELS_IMPLEMENTED",
    "SINGLE_SHEET_FIXTURE_AUDIT",
    "STRICT_PARITY_INVARIANT_AUDIT",
    "NATIVE_SPARROW_DIAGNOSTICS_AUDIT",
    "SERIOUS_SYNTHETIC_SINGLE_SHEET_AUDIT",
    "LV8_DERIVED_SINGLE_SHEET_AUDIT",
    "REAL_DXF_ONE_SHEET_SMOKE_AUDIT",
    "NEGATIVE_FIXTURE_AUDIT",
    "LEGACY_CORE_REGRESSION_GATE",
    "BUILD_TEST_RESULTS",
]

PASS_TOKENS = [
    "Q26_SINGLE_SHEET_SUITE: IMPLEMENTED",
    "VALIDATION_LEVELS: MICRO_TO_LV8_DERIVED_SINGLE_SHEET",
    "POSITIVE_FIXTURES: ALL_REQUIRE_STATUS_OK",
    "SHEET_SCOPE: SINGLE_SHEET_ONLY",
    "NATIVE_SPARROW_FLAGS: ASSERTED",
    "COMPRESSION_STATUS: DEFERRED_ONLY",
    "LEGACY_CORE_STATUS: NOT_REINTRODUCED",
    "LV8_DERIVED_SINGLE_SHEET_VALIDATION: PASS",
    "LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE",
    "FIRST_SHEET_191_STATUS: NOT_USED",
    "FULL_276_STATUS: NOT_USED",
    "REAL_DXF_ONE_SHEET_SMOKE: RUN_OR_EXPLAINED",
    "OUT_OF_SCOPE_NEW_CHANGES: NONE",
]

FORBIDDEN_ACCEPTANCE_WORDS = [
    "first-sheet",
    "first_sheet",
    "191",
    "full_276",
    "276-piece",
    "full 276",
    "lv8 benchmark",
    "lv8 pass rate",
    "multisheet acceptance",
    "multi-sheet acceptance",
    "compression_phase",
    "run_compression",
    "CompressionPhase",
    "WorkingLayout",
    "VrsCollisionTracker",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def warn(cond: bool, msg: str) -> None:
    global PASS, WARN
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        WARN += 1
        print(f"  [WARN] {msg}")


def git_status_files() -> list[str]:
    try:
        cp = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return []
    files: list[str] = []
    for line in cp.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def allowed(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in ALLOWED_PREFIXES)


def json_fixture_paths() -> list[Path]:
    if not FIX_DIR.exists():
        return []
    return sorted(p for p in FIX_DIR.glob("*.json") if p.name != "lv8_derived_subset_manifest.json")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_lv8_smoke(text: str) -> None:
    check(LV8_SMOKE.is_file(), "LV8-derived smoke script exists")
    check("samples/real_work_dxf/0014-01H/lv8jav" in text, "LV8 smoke references real LV8 directory")
    check("run_real_dxf_sparrow_pipeline.py" in text or "dxf-run" in text, "LV8 smoke uses existing DXF pipeline")
    check("dxf~" in text or "*.dxf~" in text or "endswith(\".dxf\")" in text, "LV8 smoke excludes/filters backup DXF files")
    check("1500" in text and "3000" in text, "LV8 smoke enforces 1500x3000 stock")
    check("40" in text and "80" in text, "LV8 smoke enforces 40-80 instance range")
    check("spacing_mm" in text and "margin_mm" in text, "LV8 smoke sets spacing/margin")
    check("unplaced_count" in text and re.search(r"unplaced_count[^\n]{0,80}0", text), "LV8 smoke checks unplaced_count == 0")
    check("placements_count" in text and "selected_instance_count" in text, "LV8 smoke checks placement count against selected instance count")
    check("sheet_002.dxf" in text, "LV8 smoke checks no second sheet artifact")
    check("sheet_index" in text or "sheet 0" in text.lower() or "sheet_001" in text, "LV8 smoke checks first-sheet-only output")
    check("lv8_derived_subset_manifest.json" in text, "LV8 smoke writes/uses subset manifest")
    check("first-sheet-191" not in text.lower() and "full-276" not in text.lower(), "LV8 smoke does not use forbidden LV8 benchmark labels")


def main() -> int:
    print("SGH-Q26 revised single-sheet Sparrow validation suite smoke")

    test_text = read(TEST)
    lv8_text = read(LV8_SMOKE)
    report = read(REPORT)

    check(TEST.is_file(), "Rust integration test file exists")
    check(bool(test_text), "Rust integration test file is readable")
    check(REPORT.is_file(), "Q26 report exists")

    for name in REQUIRED_TESTS:
        check(name in test_text, f"required Rust test exists: {name}")

    required_routes = [
        "jagua_optimizer_phase1_outer_only",
        "sparrow_cde",
        "cde",
        "adapter::solve",
        "SolverInput",
    ]
    for token in required_routes:
        check(token in test_text, f"integration suite references {token}")

    required_assert_tokens = [
        "sheet_index",
        "sheet_count_used",
        "sparrow_cde",
        "sparrow_invoked",
        "sparrow_converged",
        "sparrow_native_model_active",
        "sparrow_native_tracker_active",
        "sparrow_old_core_used",
        "sparrow_compression_passes",
        "loss_bbox_proxy_used_as_primary",
        "collision_backend_diagnostics",
        "bbox_fallback_queries",
    ]
    for token in required_assert_tokens:
        check(token in test_text, f"integration suite asserts/mentions {token}")

    check('status, "ok"' in test_text or 'status == "ok"' in test_text or '"ok"' in test_text,
          "positive Rust tests require status ok")
    check("partial" in test_text and "unsupported" in test_text,
          "negative overcapacity test handles partial/unsupported honestly")

    fixtures = json_fixture_paths()
    if fixtures:
        for path in fixtures:
            try:
                payload = load_json(path)
            except Exception as exc:
                check(False, f"fixture {rel(path)} is valid JSON: {exc}")
                continue
            stocks = payload.get("stocks") or payload.get("stocks_dxf")
            check(isinstance(stocks, list) and len(stocks) == 1, f"{rel(path)} has exactly one stock")
            if isinstance(stocks, list) and stocks:
                check(stocks[0].get("quantity") == 1, f"{rel(path)} stock quantity is 1")
            if "optimizer_pipeline" in payload:
                check(payload.get("optimizer_pipeline") == "sparrow_cde", f"{rel(path)} uses sparrow_cde")
            if "collision_backend" in payload:
                check(payload.get("collision_backend") == "cde", f"{rel(path)} uses cde backend")
            if "solver_profile" in payload:
                check(payload.get("solver_profile") == "jagua_optimizer_phase1_outer_only",
                      f"{rel(path)} uses phase1/sparrow profile")
    else:
        warn(False, "no JSON fixture files found; assuming inline Rust JSON fixtures")

    check_lv8_smoke(lv8_text)

    # If manifest exists, validate basic contract. If it does not exist yet, the report must explain.
    if LV8_MANIFEST.exists():
        try:
            payload = load_json(LV8_MANIFEST)
            total = int(payload.get("total_selected_instances", payload.get("selected_instance_count", -1)))
            check(40 <= total <= 80, "LV8 manifest total selected instances is within 40-80")
            files = payload.get("selected_files") or payload.get("parts") or []
            check(isinstance(files, list) and len(files) >= 2, "LV8 manifest covers multiple source files")
        except Exception as exc:
            check(False, f"LV8 manifest is valid and auditable: {exc}")
    else:
        warn(False, "LV8 manifest not found yet; must be produced by LV8 smoke/report")

    # Check Rust validation suite strictly. LV8 wording is allowed only in the LV8 smoke/report/canvas.
    for word in FORBIDDEN_ACCEPTANCE_WORDS:
        check(word.lower() not in test_text.lower(), f"Q26 Rust test source avoids forbidden token: {word}")

    # Check LV8 smoke for benchmark/multisheet forbidden claims while allowing normal LV8 path references.
    for word in ["first-sheet", "first_sheet", "191", "full_276", "full 276", "lv8 benchmark", "multisheet acceptance", "multi-sheet acceptance", "compression_phase", "run_compression", "CompressionPhase", "WorkingLayout", "VrsCollisionTracker"]:
        check(word.lower() not in lv8_text.lower(), f"LV8 smoke avoids forbidden acceptance token: {word}")

    for header in REPORT_HEADERS:
        check(header in report, f"report contains section {header}")

    if "SGH-Q26_STATUS: PASS" in report:
        for token in PASS_TOKENS:
            check(token in report, f"PASS report contains required token: {token}")
        check("PASS_WITH_NOTES" not in report or "SGH-Q26_STATUS: PASS_WITH_NOTES" not in report,
              "PASS report is not PASS_WITH_NOTES")

    status_files = git_status_files()
    if status_files:
        out_of_scope = [p for p in status_files if not allowed(p)]
        unreported = [p for p in out_of_scope if p not in report]
        check(not unreported, "all current out-of-scope dirty files are pre-reported or absent")
    else:
        warn(False, "git status unavailable or clean; scope gate checked by report only")

    print(f"SGH-Q26 revised smoke summary: PASS={PASS} WARN={WARN} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
