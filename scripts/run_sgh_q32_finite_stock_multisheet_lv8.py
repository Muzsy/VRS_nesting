#!/usr/bin/env python3
"""SGH-Q32 LV8 full-276 finite-stock multisheet benchmark runner.

Runs three benchmark cases for the sparrow_cde_multisheet pipeline on the
full 276-instance LV8 part set:

  Case 01 — 2×1500×3000mm  (hard gate: ok, placed=276, used_sheets<=2)
  Case 02 — 3×1500×3000mm  (hard gate: ok, placed=276, used_sheets<=2)
  Case 03 — 1×1500×3000 + 2×1000×2000mm  (pass as ok or correct partial)

Outputs:
  artifacts/benchmarks/sgh_q32/outputs/case_01_output.json
  artifacts/benchmarks/sgh_q32/outputs/case_02_output.json
  artifacts/benchmarks/sgh_q32/outputs/case_03_output.json
  artifacts/benchmarks/sgh_q32/sgh_q32_summary.json
  artifacts/benchmarks/sgh_q32/sgh_q32_report.md

Exit codes:
  0  PASS (all three cases pass their gates)
  1  FAIL
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
INPUTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q32" / "inputs"
OUTPUTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q32" / "outputs"
ARTIFACTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q32"

CASE_FILES = {
    "case_01": INPUTS_DIR / "case_01_2x1500x3000.json",
    "case_02": INPUTS_DIR / "case_02_3x1500x3000.json",
    "case_03": INPUTS_DIR / "case_03_1x1500x3000_2x1000x2000.json",
}

TIME_LIMIT_S = 1200


# ── Solver runner ────────────────────────────────────────────────────────────

def run_solver(case_id: str, input_path: Path, time_limit: int = TIME_LIMIT_S) -> dict[str, Any]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS_DIR / f"{case_id}_output.json"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "output.json"
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                [str(LOCAL_BIN), "--input", str(input_path), "--output", str(tmp_out)],
                capture_output=True,
                text=True,
                timeout=time_limit + 180,
            )
        except subprocess.TimeoutExpired:
            return {"case_id": case_id, "status": "timeout", "error": "solver timed out"}
        except FileNotFoundError:
            return {"case_id": case_id, "status": "error",
                    "error": f"binary not found: {LOCAL_BIN}"}
        wall_s = time.monotonic() - t0

        if tmp_out.exists():
            try:
                output = json.loads(tmp_out.read_text())
                out_path.write_text(json.dumps(output, indent=2))
                output["_wall_s"] = round(wall_s, 2)
                return output
            except Exception as e:
                return {"case_id": case_id, "status": "error",
                        "error": f"output parse error: {e}"}

        return {"case_id": case_id, "status": "error",
                "error": proc.stderr[:500] or "no output file"}


# ── Diagnostics extraction ───────────────────────────────────────────────────

def od(output: dict) -> dict:
    return output.get("optimizer_diagnostics") or {}


def metrics(output: dict) -> dict:
    return output.get("metrics") or {}


def extract_ms(output: dict) -> dict[str, Any]:
    d = od(output)
    m = metrics(output)
    return {
        "status": output.get("status", "unknown"),
        "placed_count": m.get("placed_count", 0),
        "unplaced_count": m.get("unplaced_count", 0),
        "pipeline_used": d.get("pipeline_used", "?"),
        "sparrow_ms_active": d.get("sparrow_ms_active"),
        "sparrow_ms_status": d.get("sparrow_ms_status"),
        "sparrow_ms_available_sheet_count": d.get("sparrow_ms_available_sheet_count"),
        "sparrow_ms_used_sheet_count": d.get("sparrow_ms_used_sheet_count"),
        "sparrow_ms_used_sheet_indices": d.get("sparrow_ms_used_sheet_indices"),
        "sparrow_ms_used_sheet_area": d.get("sparrow_ms_used_sheet_area"),
        "sparrow_ms_placed_part_area": d.get("sparrow_ms_placed_part_area"),
        "sparrow_ms_utilization_pct": d.get("sparrow_ms_utilization_pct"),
        "sparrow_ms_total_instances": d.get("sparrow_ms_total_instances"),
        "sparrow_ms_placed_instances": d.get("sparrow_ms_placed_instances"),
        "sparrow_ms_unplaced_instances": d.get("sparrow_ms_unplaced_instances"),
        "sparrow_ms_attempts": d.get("sparrow_ms_attempts"),
        "sparrow_ms_candidate_subsets": d.get("sparrow_ms_candidate_subsets"),
        "sparrow_ms_best_full_solution_found": d.get("sparrow_ms_best_full_solution_found"),
        "sparrow_ms_stock_exhausted": d.get("sparrow_ms_stock_exhausted"),
        "sparrow_ms_final_pairs": d.get("sparrow_ms_final_pairs"),
        "sparrow_ms_boundary_violations": d.get("sparrow_ms_boundary_violations"),
        "sparrow_ms_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "sparrow_ms_best_score": d.get("sparrow_ms_best_score"),
        "sparrow_q31_base_shape_cache_build_ms": d.get("sparrow_q31_base_shape_cache_build_ms"),
        "sparrow_q31_prepare_base_shape_native_hotpath_calls": d.get(
            "sparrow_q31_prepare_base_shape_native_hotpath_calls"),
        "unplaced": output.get("unplaced", []),
        "_wall_s": output.get("_wall_s"),
    }


# ── Gate evaluation ──────────────────────────────────────────────────────────

def evaluate_case01(ms: dict) -> tuple[str, list[str]]:
    fails = []
    if ms["status"] != "ok":
        fails.append(f"status={ms['status']!r} != ok")
    if ms["placed_count"] != 276:
        fails.append(f"placed_count={ms['placed_count']} != 276")
    if ms["unplaced_count"] != 0:
        fails.append(f"unplaced_count={ms['unplaced_count']} != 0")
    if (ms["sparrow_ms_final_pairs"] or 0) != 0:
        fails.append(f"sparrow_ms_final_pairs={ms['sparrow_ms_final_pairs']} != 0")
    if (ms["sparrow_ms_boundary_violations"] or 0) != 0:
        fails.append(f"sparrow_ms_boundary_violations={ms['sparrow_ms_boundary_violations']} != 0")
    used = ms["sparrow_ms_used_sheet_count"] or 99
    if used > 2:
        fails.append(f"sparrow_ms_used_sheet_count={used} > 2")
    util = ms["sparrow_ms_utilization_pct"] or 0.0
    if util <= 0.0:
        fails.append(f"sparrow_ms_utilization_pct={util} <= 0 (must be positive)")
    if util > 100.0:
        fails.append(f"sparrow_ms_utilization_pct={util:.2f} > 100 (polygon area basis required)")
    placed_area = ms["sparrow_ms_placed_part_area"] or 0.0
    sheet_area = ms["sparrow_ms_used_sheet_area"] or 0.0
    if sheet_area > 0 and placed_area > sheet_area + 1.0:
        fails.append(f"placed_part_area={placed_area:.0f} > used_sheet_area={sheet_area:.0f}")
    runtime_ms = ms["sparrow_ms_runtime_ms"] or 0.0
    if runtime_ms > TIME_LIMIT_S * 1000 + 5000:
        fails.append(f"sparrow_ms_runtime_ms={runtime_ms:.0f} > {TIME_LIMIT_S * 1000 + 5000} (time limit exceeded)")
    wall_s = ms.get("_wall_s") or 0.0
    if wall_s > TIME_LIMIT_S + 5:
        fails.append(f"wall_s={wall_s:.1f} > {TIME_LIMIT_S + 5} (wall time exceeded)")
    return ("PASS" if not fails else "FAIL"), fails


def evaluate_case02(ms: dict) -> tuple[str, list[str]]:
    fails = []
    if ms["status"] != "ok":
        fails.append(f"status={ms['status']!r} != ok")
    if ms["placed_count"] != 276:
        fails.append(f"placed_count={ms['placed_count']} != 276")
    if ms["unplaced_count"] != 0:
        fails.append(f"unplaced_count={ms['unplaced_count']} != 0")
    if (ms["sparrow_ms_final_pairs"] or 0) != 0:
        fails.append(f"sparrow_ms_final_pairs={ms['sparrow_ms_final_pairs']} != 0")
    if (ms["sparrow_ms_boundary_violations"] or 0) != 0:
        fails.append(f"sparrow_ms_boundary_violations={ms['sparrow_ms_boundary_violations']} != 0")
    used = ms["sparrow_ms_used_sheet_count"] or 99
    if used > 2:
        fails.append(f"sparrow_ms_used_sheet_count={used} > 2 (3 available but only <=2 should be used)")
    used_area = ms["sparrow_ms_used_sheet_area"] or 0.0
    if used_area > 9_000_000.0:
        fails.append(f"sparrow_ms_used_sheet_area={used_area:.0f} > 9000000")
    util = ms["sparrow_ms_utilization_pct"] or 0.0
    if util <= 0.0:
        fails.append(f"sparrow_ms_utilization_pct={util} <= 0 (must be positive)")
    if util > 100.0:
        fails.append(f"sparrow_ms_utilization_pct={util:.2f} > 100 (polygon area basis required)")
    placed_area = ms["sparrow_ms_placed_part_area"] or 0.0
    if used_area > 0 and placed_area > used_area + 1.0:
        fails.append(f"placed_part_area={placed_area:.0f} > used_sheet_area={used_area:.0f}")
    runtime_ms = ms["sparrow_ms_runtime_ms"] or 0.0
    if runtime_ms > TIME_LIMIT_S * 1000 + 5000:
        fails.append(f"sparrow_ms_runtime_ms={runtime_ms:.0f} > {TIME_LIMIT_S * 1000 + 5000} (time limit exceeded)")
    wall_s = ms.get("_wall_s") or 0.0
    if wall_s > TIME_LIMIT_S + 5:
        fails.append(f"wall_s={wall_s:.1f} > {TIME_LIMIT_S + 5} (wall time exceeded)")
    return ("PASS" if not fails else "FAIL"), fails


def evaluate_case03(ms: dict) -> tuple[str, list[str]]:
    """Case03 passes as ok (all 276 placed) OR as correct stock-exhausted partial."""
    status = ms["status"]
    placed = ms["placed_count"]
    unplaced_list = ms["unplaced"]
    final_pairs = ms["sparrow_ms_final_pairs"] or 0
    boundary_viol = ms["sparrow_ms_boundary_violations"] or 0
    stock_exhausted = ms["sparrow_ms_stock_exhausted"]
    used = ms["sparrow_ms_used_sheet_count"] or 0

    fails = []

    if status == "ok":
        # OK path: everything placed
        if placed != 276:
            fails.append(f"ok status but placed_count={placed} != 276")
        if ms["unplaced_count"] != 0:
            fails.append(f"ok status but unplaced_count={ms['unplaced_count']} != 0")
        if final_pairs != 0:
            fails.append(f"ok status but final_pairs={final_pairs} != 0")
        if boundary_viol != 0:
            fails.append(f"ok status but boundary_violations={boundary_viol} != 0")
    elif status == "partial":
        # Partial path: must be collision-free, stock_exhausted, explicit unplaced reasons
        if placed <= 0:
            fails.append(f"partial status but placed_count={placed} <= 0")
        if not unplaced_list:
            fails.append("partial status but unplaced list is empty")
        if not stock_exhausted:
            fails.append("partial status but sparrow_ms_stock_exhausted != true")
        if used != 3:
            fails.append(f"partial status: sparrow_ms_used_sheet_count={used} != 3 (all sheets must be tried)")
        if final_pairs != 0:
            fails.append(f"partial output has final_pairs={final_pairs} != 0 (must be collision-free)")
        if boundary_viol != 0:
            fails.append(f"partial output has boundary_violations={boundary_viol} != 0")
        # All unplaced must have explicit valid reasons
        valid_reasons = {
            "INSUFFICIENT_STOCK_CAPACITY",
            "STOCK_EXHAUSTED_PARTIAL",
            "UNRESOLVED_AFTER_STOCK_EXHAUSTED",
            "PART_NEVER_FITS_STOCK",
        }
        for u in unplaced_list:
            r = u.get("reason", "")
            if not r:
                fails.append(f"unplaced {u.get('part_id')!r} has empty reason")
            elif r not in valid_reasons:
                fails.append(f"unplaced {u.get('part_id')!r} has invalid reason: {r!r}")
    else:
        fails.append(f"status={status!r} is neither ok nor partial")

    # Cross-status: utilization and time-limit gates always apply
    util = ms["sparrow_ms_utilization_pct"] or 0.0
    if util > 100.0:
        fails.append(f"sparrow_ms_utilization_pct={util:.2f} > 100 (polygon area basis required)")
    placed_area = ms["sparrow_ms_placed_part_area"] or 0.0
    sheet_area = ms["sparrow_ms_used_sheet_area"] or 0.0
    if sheet_area > 0 and placed_area > sheet_area + 1.0:
        fails.append(f"placed_part_area={placed_area:.0f} > used_sheet_area={sheet_area:.0f}")
    runtime_ms = ms["sparrow_ms_runtime_ms"] or 0.0
    if runtime_ms > TIME_LIMIT_S * 1000 + 5000:
        fails.append(f"sparrow_ms_runtime_ms={runtime_ms:.0f} > {TIME_LIMIT_S * 1000 + 5000} (time limit exceeded)")
    wall_s = ms.get("_wall_s") or 0.0
    if wall_s > TIME_LIMIT_S + 5:
        fails.append(f"wall_s={wall_s:.1f} > {TIME_LIMIT_S + 5} (wall time exceeded)")

    return ("PASS" if not fails else "FAIL"), fails


# ── Report writing ───────────────────────────────────────────────────────────

def _gate_row(label: str, val: Any, gate: str, ok: bool) -> str:
    icon = "PASS" if ok else "FAIL"
    return f"| {label} | {val} | {gate} | {icon} |"


def write_report(cases: list[dict], summary_status: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    c1 = next((c for c in cases if c["case_id"] == "case_01"), {})
    c2 = next((c for c in cases if c["case_id"] == "case_02"), {})
    c3 = next((c for c in cases if c["case_id"] == "case_03"), {})

    m1 = c1.get("ms", {})
    m2 = c2.get("ms", {})
    m3 = c3.get("ms", {})

    lines = [
        "# SGH-Q32 Finite-Stock Sparrow Multisheet Manager — LV8 Benchmark Report",
        "",
        "## Summary",
        "",
        f"**Status:** `{summary_status}`",
        "",
        f"| Case | Status | Placed | Used Sheets | Final Pairs | Gate |",
        f"|---|---|---|---|---|---|",
        f"| Case 01 (2×1500×3000) | {m1.get('status','?')} | {m1.get('placed_count','?')} "
        f"| {m1.get('sparrow_ms_used_sheet_count','?')} "
        f"| {m1.get('sparrow_ms_final_pairs','?')} "
        f"| {c1.get('case_status','?')} |",
        f"| Case 02 (3×1500×3000) | {m2.get('status','?')} | {m2.get('placed_count','?')} "
        f"| {m2.get('sparrow_ms_used_sheet_count','?')} "
        f"| {m2.get('sparrow_ms_final_pairs','?')} "
        f"| {c2.get('case_status','?')} |",
        f"| Case 03 (1×1500×3000+2×1000×2000) | {m3.get('status','?')} | {m3.get('placed_count','?')} "
        f"| {m3.get('sparrow_ms_used_sheet_count','?')} "
        f"| {m3.get('sparrow_ms_final_pairs','?')} "
        f"| {c3.get('case_status','?')} |",
        "",
    ]

    for case in cases:
        cid = case["case_id"]
        ms = case.get("ms", {})
        cs = case.get("case_status", "?")
        fails = case.get("fails", [])
        wall = ms.get("_wall_s", "?")
        lines += [
            f"## {cid} — {cs}",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| status | {ms.get('status','?')} |",
            f"| placed_count | {ms.get('placed_count','?')} |",
            f"| unplaced_count | {ms.get('unplaced_count','?')} |",
            f"| sparrow_ms_active | {ms.get('sparrow_ms_active','?')} |",
            f"| sparrow_ms_status | {ms.get('sparrow_ms_status','?')} |",
            f"| sparrow_ms_available_sheet_count | {ms.get('sparrow_ms_available_sheet_count','?')} |",
            f"| sparrow_ms_used_sheet_count | {ms.get('sparrow_ms_used_sheet_count','?')} |",
            f"| sparrow_ms_used_sheet_indices | {ms.get('sparrow_ms_used_sheet_indices','?')} |",
            f"| sparrow_ms_used_sheet_area | {ms.get('sparrow_ms_used_sheet_area','?')} |",
            f"| sparrow_ms_utilization_pct | {ms.get('sparrow_ms_utilization_pct','?')} |",
            f"| sparrow_ms_total_instances | {ms.get('sparrow_ms_total_instances','?')} |",
            f"| sparrow_ms_placed_instances | {ms.get('sparrow_ms_placed_instances','?')} |",
            f"| sparrow_ms_unplaced_instances | {ms.get('sparrow_ms_unplaced_instances','?')} |",
            f"| sparrow_ms_attempts | {ms.get('sparrow_ms_attempts','?')} |",
            f"| sparrow_ms_candidate_subsets | {ms.get('sparrow_ms_candidate_subsets','?')} |",
            f"| sparrow_ms_best_full_solution_found | {ms.get('sparrow_ms_best_full_solution_found','?')} |",
            f"| sparrow_ms_stock_exhausted | {ms.get('sparrow_ms_stock_exhausted','?')} |",
            f"| sparrow_ms_final_pairs | {ms.get('sparrow_ms_final_pairs','?')} |",
            f"| sparrow_ms_boundary_violations | {ms.get('sparrow_ms_boundary_violations','?')} |",
            f"| sparrow_ms_runtime_ms | {ms.get('sparrow_ms_runtime_ms','?')} |",
            f"| sparrow_q31_cache_build_ms | {ms.get('sparrow_q31_base_shape_cache_build_ms','?')} |",
            f"| sparrow_q31_hotpath_calls | {ms.get('sparrow_q31_prepare_base_shape_native_hotpath_calls','?')} |",
            f"| wall_s | {wall} |",
            "",
        ]
        if fails:
            lines.append(f"**Gate failures:**")
            for f in fails:
                lines.append(f"- {f}")
            lines.append("")

    lines += [
        "---",
        "",
        f"Q32_STATUS: {summary_status}",
        f"Q32_CASE01_STATUS: {c1.get('case_status','?')}",
        f"Q32_CASE02_STATUS: {c2.get('case_status','?')}",
        f"Q32_CASE03_STATUS: {c3.get('case_status','?')}",
        f"Q32_CASE01_PLACED: {m1.get('placed_count','?')}",
        f"Q32_CASE02_PLACED: {m2.get('placed_count','?')}",
        f"Q32_CASE03_PLACED: {m3.get('placed_count','?')}",
        f"Q32_CASE01_USED_SHEETS: {m1.get('sparrow_ms_used_sheet_count','?')}",
        f"Q32_CASE02_USED_SHEETS: {m2.get('sparrow_ms_used_sheet_count','?')}",
        f"Q32_CASE03_USED_SHEETS: {m3.get('sparrow_ms_used_sheet_count','?')}",
        f"Q32_CASE01_FINAL_PAIRS: {m1.get('sparrow_ms_final_pairs','?')}",
        f"Q32_CASE02_FINAL_PAIRS: {m2.get('sparrow_ms_final_pairs','?')}",
        f"Q32_CASE03_FINAL_PAIRS: {m3.get('sparrow_ms_final_pairs','?')}",
        f"Q32_CASE03_UNPLACED: {m3.get('unplaced_count','?')}",
        f"Q32_FINAL_VERDICT: {'All gates passed' if summary_status == 'PASS' else 'One or more gates failed'}",
    ]

    out = ARTIFACTS_DIR / "sgh_q32_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"Written: {out}")


def write_summary(cases: list[dict], summary_status: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "task": "sgh_q32_finite_stock_sparrow_multisheet_manager",
        "status": summary_status,
        "cases": [
            {
                "case_id": c["case_id"],
                "case_status": c.get("case_status", "?"),
                "ms": c.get("ms", {}),
                "fails": c.get("fails", []),
            }
            for c in cases
        ],
    }
    out = ARTIFACTS_DIR / "sgh_q32_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"Written: {out}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    if not LOCAL_BIN.exists():
        print(f"ERROR: release binary not found: {LOCAL_BIN}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        return 1

    print("=== SGH-Q32 LV8 full-276 finite-stock multisheet benchmark ===")
    print(f"Binary: {LOCAL_BIN}")
    print(f"Time limit per case: {TIME_LIMIT_S}s")
    print()

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    cases = []

    for i, (case_id, input_path) in enumerate(CASE_FILES.items(), 1):
        if not input_path.exists():
            print(f"ERROR: input not found: {input_path}")
            return 1

        print(f"[{i}/3] {case_id} — {input_path.name} ...")
        output = run_solver(case_id, input_path)
        ms = extract_ms(output)

        if case_id == "case_01":
            case_status, fails = evaluate_case01(ms)
        elif case_id == "case_02":
            case_status, fails = evaluate_case02(ms)
        else:
            case_status, fails = evaluate_case03(ms)

        print(
            f"  status={ms.get('status','?')} "
            f"placed={ms.get('placed_count','?')} "
            f"used_sheets={ms.get('sparrow_ms_used_sheet_count','?')} "
            f"final_pairs={ms.get('sparrow_ms_final_pairs','?')} "
            f"boundary_viol={ms.get('sparrow_ms_boundary_violations','?')} "
            f"util={ms.get('sparrow_ms_utilization_pct','?')}% "
            f"wall={ms.get('_wall_s','?')}s "
            f"→ {case_status}"
        )
        if fails:
            for f in fails:
                print(f"    FAIL: {f}")

        cases.append({"case_id": case_id, "case_status": case_status, "ms": ms, "fails": fails})

    all_pass = all(c["case_status"] == "PASS" for c in cases)
    summary_status = "PASS" if all_pass else "FAIL"

    print()
    print(f"Q32_STATUS: {summary_status}")
    for c in cases:
        print(f"  {c['case_id']}: {c['case_status']}")

    write_summary(cases, summary_status)
    write_report(cases, summary_status)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
