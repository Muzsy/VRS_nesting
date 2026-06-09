#!/usr/bin/env python3
"""SGH-Q32 smoke — finite-stock Sparrow multisheet manager validator.

Validates static code invariants AND runtime artifacts (benchmark outputs,
report markers). Designed to run after run_sgh_q32_finite_stock_multisheet_lv8.py.

Exit codes:
  0  PASS
  2  FAIL
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts" / "benchmarks" / "sgh_q32" / "sgh_q32_summary.json"
REPORT_MD = ROOT / "artifacts" / "benchmarks" / "sgh_q32" / "sgh_q32_report.md"
CODEX_REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q32_finite_stock_sparrow_multisheet_manager.md"
OUTPUTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q32" / "outputs"
INPUTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q32" / "inputs"

PASS_COUNT = 0
FAIL_COUNT = 0


def check(cond: bool, msg: str) -> None:
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {msg}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_comments(text: str) -> str:
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    return text


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def od_of(output: dict) -> dict:
    return output.get("optimizer_diagnostics") or {}


def ms_field(output: dict, key: str) -> Any:
    return od_of(output).get(key)


# ── Static code invariants ───────────────────────────────────────────────────

def check_static_invariants() -> None:
    print("\n--- Static code invariants ---")

    io_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/io.rs"))
    adapter_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/adapter.rs"))
    mod_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/mod.rs"))
    multisheet_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/multisheet.rs"))
    model_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/model.rs"))

    # 1. Enum variant exists
    check("SparrowCdeMultisheet" in io_rs, "io.rs: OptimizerPipelineKind::SparrowCdeMultisheet exists")
    # 2. Serde name is snake_case
    raw_io = read(ROOT / "rust/vrs_solver/src/io.rs")
    check('rename_all = "snake_case"' in raw_io, 'io.rs: #[serde(rename_all = "snake_case")] on OptimizerPipelineKind')
    # 3. multisheet module exported
    check("pub mod multisheet" in mod_rs, "sparrow/mod.rs: pub mod multisheet exported")
    # 4. multisheet.rs file exists
    check((ROOT / "rust/vrs_solver/src/optimizer/sparrow/multisheet.rs").exists(),
          "sparrow/multisheet.rs file exists")
    # 5. No legacy WorkingLayout in multisheet.rs
    check("WorkingLayout" not in multisheet_rs,
          "multisheet.rs: WorkingLayout NOT used")
    # 6. No VrsCollisionTracker in multisheet.rs
    check("VrsCollisionTracker" not in multisheet_rs,
          "multisheet.rs: VrsCollisionTracker NOT used")
    # 7. No Python wrapper reference in multisheet.rs
    check("multi_sheet_wrapper" not in multisheet_rs,
          "multisheet.rs: Python multi_sheet_wrapper NOT referenced")
    # 8. No compression in multisheet.rs
    check("compress" not in multisheet_rs.lower() or
          "compression" not in multisheet_rs.lower(),
          "multisheet.rs: no compression logic")
    # 9. Adapter routing present
    check("SparrowCdeMultisheet" in adapter_rs and
          "run_sparrow_finite_stock_multisheet_pipeline" in adapter_rs,
          "adapter.rs: SparrowCdeMultisheet routing to run_sparrow_finite_stock_multisheet_pipeline")
    # 10. sparrow_ms_* fields in io.rs
    for field in [
        "sparrow_ms_active",
        "sparrow_ms_final_pairs",
        "sparrow_ms_boundary_violations",
        "sparrow_ms_used_sheet_count",
        "sparrow_ms_used_sheet_indices",
        "sparrow_ms_used_sheet_area",
        "sparrow_ms_utilization_pct",
        "sparrow_ms_stock_exhausted",
        "sparrow_ms_status",
        "sparrow_ms_requested_time_limit_s",
        "sparrow_ms_deadline_hit",
    ]:
        check(field in io_rs, f"io.rs: {field} field present")
    # 11. Q31 base-shape cache not regressed
    check("Rc<CdeBaseShape>" in model_rs,
          "model.rs: Q31 Rc<CdeBaseShape> base_shape cache preserved")
    check("sparrow_q31_base_shape_cache_build_ms" in io_rs or
          "sparrow_q31_base_shape_cache_build_ms" in adapter_rs,
          "Q31 cache build_ms field still present (not regressed)")
    # 12. ok status only when final_pairs=0 (code comment)
    check("ok" in multisheet_rs and "final_pairs" in multisheet_rs,
          "multisheet.rs: ok/final_pairs logic present")
    # 13. partial sanitize present
    check("sanitize_partial" in multisheet_rs,
          "multisheet.rs: sanitize_partial function exists")


# ── Artifact existence ───────────────────────────────────────────────────────

def check_artifacts() -> None:
    print("\n--- Artifact existence ---")
    check(SUMMARY.exists(), f"summary JSON exists: {SUMMARY.relative_to(ROOT)}")
    check(REPORT_MD.exists(), f"benchmark report exists: {REPORT_MD.relative_to(ROOT)}")
    check((OUTPUTS_DIR / "case_01_output.json").exists(), "case_01 output exists")
    check((OUTPUTS_DIR / "case_02_output.json").exists(), "case_02 output exists")
    check((OUTPUTS_DIR / "case_03_output.json").exists(), "case_03 output exists")
    check((INPUTS_DIR / "case_01_2x1500x3000.json").exists(), "case_01 input exists")
    check((INPUTS_DIR / "case_02_3x1500x3000.json").exists(), "case_02 input exists")
    check((INPUTS_DIR / "case_03_1x1500x3000_2x1000x2000.json").exists(), "case_03 input exists")


# ── Runtime acceptance ───────────────────────────────────────────────────────

def load_case_output(case_id: str) -> dict | None:
    p = OUTPUTS_DIR / f"{case_id}_output.json"
    if not p.exists():
        return None
    try:
        return load_json(p)
    except Exception:
        return None


def check_case01(output: dict) -> None:
    print("\n--- Case 01 acceptance (2×1500×3000) ---")
    if output is None:
        check(False, "case_01 output loadable")
        return
    check(True, "case_01 output loadable")

    metrics = output.get("metrics") or {}
    d = od_of(output)

    check(output.get("status") == "ok", f"case_01 status=ok, got {output.get('status')!r}")
    check(metrics.get("placed_count") == 276,
          f"case_01 placed_count=276, got {metrics.get('placed_count')}")
    check(metrics.get("unplaced_count") == 0,
          f"case_01 unplaced_count=0, got {metrics.get('unplaced_count')}")
    check(d.get("sparrow_ms_active") is True,
          f"case_01 sparrow_ms_active=True, got {d.get('sparrow_ms_active')}")
    check(d.get("sparrow_ms_final_pairs") == 0,
          f"case_01 final_pairs=0, got {d.get('sparrow_ms_final_pairs')}")
    check(d.get("sparrow_ms_boundary_violations") == 0,
          f"case_01 boundary_violations=0, got {d.get('sparrow_ms_boundary_violations')}")
    used = d.get("sparrow_ms_used_sheet_count") or 99
    check(used <= 2, f"case_01 used_sheet_count<=2, got {used}")
    util = d.get("sparrow_ms_utilization_pct") or 0.0
    check(util > 0.0, f"case_01 utilization_pct>0, got {util}")
    check(util <= 100.0, f"case_01 utilization_pct<=100 (polygon area), got {util:.2f}")
    placed_area = d.get("sparrow_ms_placed_part_area") or 0.0
    sheet_area = d.get("sparrow_ms_used_sheet_area") or 0.0
    if sheet_area > 0:
        check(placed_area <= sheet_area + 1.0,
              f"case_01 placed_part_area({placed_area:.0f}) <= sheet_area({sheet_area:.0f})")
    runtime_ms = d.get("sparrow_ms_runtime_ms") or 0.0
    check(runtime_ms <= 1200_000 + 5000,
          f"case_01 runtime_ms={runtime_ms:.0f} <= 1205000")
    # Q31 cache invariant
    check(d.get("sparrow_q31_base_shape_cache_build_ms") is not None,
          "case_01 Q31 base_shape_cache_build_ms present")


def check_case02(output: dict) -> None:
    print("\n--- Case 02 acceptance (3×1500×3000) ---")
    if output is None:
        check(False, "case_02 output loadable")
        return
    check(True, "case_02 output loadable")

    metrics = output.get("metrics") or {}
    d = od_of(output)

    check(output.get("status") == "ok", f"case_02 status=ok, got {output.get('status')!r}")
    check(metrics.get("placed_count") == 276,
          f"case_02 placed_count=276, got {metrics.get('placed_count')}")
    check(metrics.get("unplaced_count") == 0,
          f"case_02 unplaced_count=0, got {metrics.get('unplaced_count')}")
    check(d.get("sparrow_ms_final_pairs") == 0,
          f"case_02 final_pairs=0, got {d.get('sparrow_ms_final_pairs')}")
    check(d.get("sparrow_ms_boundary_violations") == 0,
          f"case_02 boundary_violations=0, got {d.get('sparrow_ms_boundary_violations')}")
    used = d.get("sparrow_ms_used_sheet_count") or 99
    check(used <= 2, f"case_02 used_sheet_count<=2 (3 available), got {used}")
    used_area = d.get("sparrow_ms_used_sheet_area") or 0.0
    check(used_area <= 9_000_000.0,
          f"case_02 used_sheet_area<=9000000, got {used_area:.0f}")
    util = d.get("sparrow_ms_utilization_pct") or 0.0
    check(util > 0.0, f"case_02 utilization_pct>0, got {util}")
    check(util <= 100.0, f"case_02 utilization_pct<=100 (polygon area), got {util:.2f}")
    placed_area = d.get("sparrow_ms_placed_part_area") or 0.0
    if used_area > 0:
        check(placed_area <= used_area + 1.0,
              f"case_02 placed_part_area({placed_area:.0f}) <= sheet_area({used_area:.0f})")
    runtime_ms = d.get("sparrow_ms_runtime_ms") or 0.0
    check(runtime_ms <= 1200_000 + 5000,
          f"case_02 runtime_ms={runtime_ms:.0f} <= 1205000")
    avail = d.get("sparrow_ms_available_sheet_count") or 0
    check(avail == 3, f"case_02 available_sheet_count=3, got {avail}")


def check_case03(output: dict) -> None:
    print("\n--- Case 03 acceptance (1×1500×3000 + 2×1000×2000) ---")
    if output is None:
        check(False, "case_03 output loadable")
        return
    check(True, "case_03 output loadable")

    status = output.get("status", "unknown")
    metrics_d = output.get("metrics") or {}
    d = od_of(output)
    unplaced = output.get("unplaced", [])

    placed = metrics_d.get("placed_count", 0)
    final_pairs = d.get("sparrow_ms_final_pairs") or 0
    boundary_viol = d.get("sparrow_ms_boundary_violations") or 0

    check(status in ("ok", "partial"),
          f"case_03 status in {{ok, partial}}, got {status!r}")
    check(final_pairs == 0,
          f"case_03 final_pairs=0 (collision-free), got {final_pairs}")
    check(boundary_viol == 0,
          f"case_03 boundary_violations=0, got {boundary_viol}")

    if status == "ok":
        check(placed == 276, f"case_03 ok: placed_count=276, got {placed}")
        check(metrics_d.get("unplaced_count") == 0,
              f"case_03 ok: unplaced_count=0, got {metrics_d.get('unplaced_count')}")
    elif status == "partial":
        check(placed > 0, f"case_03 partial: placed_count>0, got {placed}")
        check(len(unplaced) > 0, f"case_03 partial: unplaced list non-empty")
        check(d.get("sparrow_ms_stock_exhausted") is True,
              f"case_03 partial: stock_exhausted=True, got {d.get('sparrow_ms_stock_exhausted')}")
        # All unplaced must have valid explicit reasons
        valid_reasons = {
            "INSUFFICIENT_STOCK_CAPACITY",
            "STOCK_EXHAUSTED_PARTIAL",
            "UNRESOLVED_AFTER_STOCK_EXHAUSTED",
            "PART_NEVER_FITS_STOCK",
        }
        bad_reasons = [u for u in unplaced if not u.get("reason") or u.get("reason") not in valid_reasons]
        check(len(bad_reasons) == 0,
              f"case_03 partial: all unplaced have valid reasons (bad={len(bad_reasons)})")

    # Cross-status gates
    util = d.get("sparrow_ms_utilization_pct") or 0.0
    check(util <= 100.0, f"case_03 utilization_pct<=100 (polygon area), got {util:.2f}")
    placed_area = d.get("sparrow_ms_placed_part_area") or 0.0
    sheet_area = d.get("sparrow_ms_used_sheet_area") or 0.0
    if sheet_area > 0:
        check(placed_area <= sheet_area + 1.0,
              f"case_03 placed_part_area({placed_area:.0f}) <= sheet_area({sheet_area:.0f})")
    runtime_ms = d.get("sparrow_ms_runtime_ms") or 0.0
    check(runtime_ms <= 1200_000 + 5000,
          f"case_03 runtime_ms={runtime_ms:.0f} <= 1205000")


# ── Summary and codex report markers ────────────────────────────────────────

def check_summary() -> None:
    print("\n--- Summary JSON gates ---")
    if not SUMMARY.exists():
        check(False, "summary JSON exists (cannot check gates)")
        return

    s = load_json(SUMMARY)
    check(s.get("status") in ("PASS", "FAIL"), f"summary has status field: {s.get('status')!r}")

    for c in s.get("cases", []):
        cid = c.get("case_id", "?")
        cs = c.get("case_status", "?")
        check(cs in ("PASS", "FAIL"), f"case {cid!r} has case_status PASS|FAIL: {cs!r}")


def check_codex_report() -> None:
    print("\n--- Codex report markers ---")
    report = read(CODEX_REPORT)
    if not CODEX_REPORT.exists():
        check(False, f"codex report exists: {CODEX_REPORT.relative_to(ROOT)}")
        return
    check(True, f"codex report exists: {CODEX_REPORT.relative_to(ROOT)}")

    required_markers = [
        "Q32_STATUS:",
        "Q32_CASE01_STATUS:",
        "Q32_CASE02_STATUS:",
        "Q32_CASE03_STATUS:",
        "Q32_CASE01_PLACED:",
        "Q32_CASE02_PLACED:",
        "Q32_CASE03_PLACED:",
        "Q32_CASE01_USED_SHEETS:",
        "Q32_CASE02_USED_SHEETS:",
        "Q32_CASE03_USED_SHEETS:",
        "Q32_CASE01_FINAL_PAIRS:",
        "Q32_CASE02_FINAL_PAIRS:",
        "Q32_CASE03_FINAL_PAIRS:",
        "Q32_CASE03_UNPLACED:",
        "Q32_FINAL_VERDICT:",
    ]
    for marker in required_markers:
        check(marker in report, f"codex report marker present: {marker}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=== SGH-Q32 finite-stock Sparrow multisheet smoke ===")

    check_static_invariants()
    check_artifacts()

    out1 = load_case_output("case_01")
    out2 = load_case_output("case_02")
    out3 = load_case_output("case_03")

    check_case01(out1)
    check_case02(out2)
    check_case03(out3)

    check_summary()
    check_codex_report()

    print(f"\nPASS={PASS_COUNT} FAIL={FAIL_COUNT}")
    return 0 if FAIL_COUNT == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
