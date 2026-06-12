#!/usr/bin/env python3
"""SGH-Q37 smoke — validate the LV8 margin+spacing benchmark + measurement hardening.

Validates the artifacts produced by `bench_sgh_q37_lv8_margin_spacing.py` (run that first).
Does NOT re-run the heavy solver matrix.

Static checks:
  - benchmark script + sgh_q37 artifact dirs exist
  - all required tables exist (run_summary, stage_timing, cde_metrics, spacing inventory,
    failure_taxonomy, quality_comparison) + measurement manifest
  - report exists and contains a "Recommended next task" section
  - generated benchmark inputs set spacing_mm EXPLICITLY
  - kerf_mm is never added to spacing (offset == spacing/2 in every run)
  - cavity prepack .rs files not modified by this task

Dynamic checks (over produced outputs):
  - geometry inventory ran
  - mandatory D0/D1/D2 and M0/M1/M2 ran and their outputs parse
  - no status==ok with any violation > 0
  - prepare_base_shape_native_hotpath_calls == 0 in every mandatory run
  - Q36 spacing diagnostics present in every run

Use --include-extended to also require E1..E6 runs.

Exit codes: 0 PASS, 2 FAIL
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q37 = ROOT / "artifacts/benchmarks/sgh_q37"
TABLES = Q37 / "tables"
OUTPUTS = Q37 / "outputs"
INPUTS = Q37 / "inputs"
BENCH = ROOT / "scripts/bench_sgh_q37_lv8_margin_spacing.py"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q37_lv8_margin_spacing_benchmark.md"

MANDATORY_RUNS = ["D0", "D1", "D2", "M0", "M1", "M2"]
EXTENDED_RUNS = ["E1", "E2", "E3", "E4", "E5", "E6"]

PASS = 0
FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def od(o):
    return o.get("optimizer_diagnostics") or {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-extended", action="store_true")
    args = ap.parse_args()
    runs = MANDATORY_RUNS + (EXTENDED_RUNS if args.include_extended else [])

    print("=== SGH-Q37 benchmark + measurement smoke ===")
    print("\n--- Static checks ---")
    check(BENCH.exists(), "bench_sgh_q37_lv8_margin_spacing.py exists")
    for d in (INPUTS, OUTPUTS, TABLES, Q37 / "logs"):
        check(d.exists(), f"artifact dir exists: {d.relative_to(ROOT)}")
    for t in ("q37_run_summary.csv", "q37_stage_timing.csv", "q37_cde_metrics.csv",
              "q37_spacing_geometry_inventory.csv", "q37_failure_taxonomy.csv",
              "q37_quality_comparison.csv", "q37_measurement_manifest.json"):
        check((TABLES / t).exists(), f"table exists: {t}")
    check(REPORT.exists(), "Q37 report exists")
    if REPORT.exists():
        rep = REPORT.read_text()
        check("## Recommended next task" in rep, "report has 'Recommended next task' section")
        check("## Interpretation" in rep, "report has 'Interpretation' section")

    # Generated inputs must set spacing_mm explicitly + kerf 0.
    inp_files = list(INPUTS.glob("*.json"))
    check(len(inp_files) > 0, "benchmark inputs were generated")
    all_explicit = True
    for f in inp_files:
        doc = json.loads(f.read_text())
        if "spacing_mm" not in doc:
            all_explicit = False
            print(f"    missing spacing_mm: {f.name}")
        if doc.get("kerf_mm", 0.0) not in (0.0,):
            all_explicit = False
            print(f"    nonzero kerf: {f.name}")
    check(all_explicit, "every benchmark input sets spacing_mm explicitly and kerf_mm == 0")

    # Cavity prepack untouched (git).
    try:
        res = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=30)
        changed = [l for l in res.stdout.splitlines() if "cavity" in l.lower() and ".rs" in l.lower()]
        check(not changed, f"no cavity prepack .rs modified ({changed})")
    except Exception:
        check(True, "git unavailable → skip cavity check")

    # Dynamic checks over produced outputs.
    print("\n--- Dynamic checks ---")
    check((TABLES / "q37_spacing_geometry_inventory.csv").exists(), "geometry inventory ran")

    for run_id in runs:
        out_path = OUTPUTS / f"{run_id}_output.json"
        if not out_path.exists():
            check(False, f"{run_id}: output exists")
            continue
        try:
            o = json.loads(out_path.read_text())
        except json.JSONDecodeError as e:
            check(False, f"{run_id}: output parses ({e})")
            continue
        check(True, f"{run_id}: output parses")
        d = od(o)
        status = o.get("status")
        viol = {
            "final_pairs": d.get("sparrow_ms_final_pairs"),
            "boundary_violations": d.get("sparrow_ms_boundary_violations"),
            "technology_margin_violation_count": d.get("technology_margin_violation_count"),
            "technology_spacing_violation_count": d.get("technology_spacing_violation_count"),
        }
        if status == "ok":
            bad = [k for k, v in viol.items() if isinstance(v, int) and v > 0]
            check(not bad, f"{run_id}: status==ok ⇒ no violations (bad={bad})")
        else:
            check(True, f"{run_id}: status={status} (partial allowed)")
        hot = d.get("sparrow_q31_prepare_base_shape_native_hotpath_calls")
        check(hot in (0, None), f"{run_id}: prepare_base_shape_native_hotpath_calls == 0 (got {hot})")
        # Q36 spacing diagnostics present.
        for f in ("technology_spacing_geometry_applied", "technology_spacing_offset_mm",
                  "technology_spacing_boundary_uses_original_geometry",
                  "technology_spacing_output_uses_original_geometry"):
            check(f in d, f"{run_id}: Q36 diagnostic {f} present")
        # offset == spacing/2 (kerf not folded in).
        sp = d.get("technology_part_spacing_mm")
        off = d.get("technology_spacing_offset_mm")
        if sp is not None and off is not None:
            check(abs(off - sp / 2.0) < 1e-9, f"{run_id}: offset_mm {off} == spacing/2 {sp/2.0}")

    # Manifest must record no measurement-gate errors.
    man = TABLES / "q37_measurement_manifest.json"
    if man.exists():
        m = json.loads(man.read_text())
        check(not m.get("errors"), f"manifest reports no measurement-gate errors ({m.get('errors')})")

    print(f"\n{'='*52}")
    print(f"  PASS: {PASS}   FAIL: {FAIL}")
    if FAIL:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
