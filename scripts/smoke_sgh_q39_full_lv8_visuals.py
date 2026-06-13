#!/usr/bin/env python3
"""SGH-Q39 smoke — validate the full LV8 visual production benchmark artifacts.

Validates the artifacts produced by `bench_sgh_q39_full_lv8_visuals.py --tier mandatory`
(run that first). Does NOT re-run the heavy solver matrix.

Static checks:
  - bench + smoke scripts exist; q39 artifact dirs exist;
  - report exists with Recommended next task + Interpretation;
  - required tables exist (run_summary, per_sheet_summary, render_summary, regression_gates,
    measurement_manifest, stage_timing, cde_metrics, quality_comparison);
  - render files for mandatory runs are present (SVG+PNG per used sheet + overview).

Dynamic checks:
  - B0 ok 191/191 1 sheet; B1 ok 276/276 2 sheets; B2 ok 276/276 used 2;
  - mandatory spacing runs (S0..S5) offset_failure_count == 0;
  - no status==ok with any violation; q31 hotpath calls == 0 in every mandatory run;
  - per used sheet: sheet_NN.svg + sheet_NN.png exist; overview.svg + overview.png exist;
  - regression_gates.json has no false mandatory gate; time_limit_cap_applied == false.

--include-extended additionally requires E0..E4 render/output presence.
Exit codes: 0 PASS, 2 FAIL
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q39 = ROOT / "artifacts/benchmarks/sgh_q39"
TABLES = Q39 / "tables"
RENDERS = Q39 / "renders"
OUTPUTS = Q39 / "outputs"
BENCH = ROOT / "scripts/bench_sgh_q39_full_lv8_visuals.py"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q39_full_lv8_visual_benchmark.md"

MANDATORY = ["B0", "B1", "B2", "B3", "S0", "S1", "S2", "S3", "S4", "S5"]
EXTENDED = ["E0", "E1", "E2", "E3", "E4"]

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


def ai(v):
    try:
        return int(float(v))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-extended", action="store_true")
    args = ap.parse_args()
    runs = MANDATORY + (EXTENDED if args.include_extended else [])

    print("=== SGH-Q39 full LV8 visual benchmark smoke ===")
    print("\n--- Static checks ---")
    check(BENCH.exists(), "bench_sgh_q39_full_lv8_visuals.py exists")
    for d in ("inputs", "outputs", "tables", "logs", "renders"):
        check((Q39 / d).exists(), f"artifact dir exists: {d}")
    for t in ("q39_run_summary.csv", "q39_per_sheet_summary.csv", "q39_stage_timing.csv",
              "q39_cde_metrics.csv", "q39_quality_comparison.csv", "q39_render_summary.csv",
              "q39_regression_gates.json", "q39_measurement_manifest.json"):
        check((TABLES / t).exists(), f"table exists: {t}")
    check(REPORT.exists(), "Q39 report exists")
    if REPORT.exists():
        rep = REPORT.read_text()
        check("## Recommended next task" in rep, "report has 'Recommended next task'")
        check("## Interpretation" in rep, "report has 'Interpretation'")

    summary = {}
    sp = TABLES / "q39_run_summary.csv"
    if sp.exists():
        summary = {r["run_id"]: r for r in csv.DictReader(sp.open())}

    print("\n--- Dynamic checks ---")
    # Baselines.
    b0 = summary.get("B0", {})
    check(b0.get("status") == "ok" and ai(b0.get("placed_count")) == 191 and ai(b0.get("unplaced_count")) == 0
          and ai(b0.get("used_sheet_count")) == 1, "B0 dense191: ok 191/191, 1 sheet")
    b1 = summary.get("B1", {})
    check(b1.get("status") == "ok" and ai(b1.get("placed_count")) == 276 and ai(b1.get("unplaced_count")) == 0
          and ai(b1.get("used_sheet_count")) == 2, "B1 full276 2-sheet: ok 276/276, 2 sheets")
    b2 = summary.get("B2", {})
    check(b2.get("status") == "ok" and ai(b2.get("placed_count")) == 276 and ai(b2.get("unplaced_count")) == 0
          and ai(b2.get("used_sheet_count")) == 2, "B2 full276 3-sheet: ok 276/276, used 2")

    # No false ok + hotpath 0 + spacing offset failures 0.
    for rid in runs:
        r = summary.get(rid)
        if not r:
            check(False, f"{rid}: present in run_summary")
            continue
        if r.get("status") == "ok":
            bad = [k for k in ("final_pairs", "boundary_violations", "technology_margin_violation_count",
                               "technology_spacing_violation_count") if (ai(r.get(k)) or 0) > 0]
            check(not bad, f"{rid}: status ok ⇒ no violations ({bad})")
        else:
            check(True, f"{rid}: status={r.get('status')} (partial allowed)")
        check((ai(r.get("q31_prepare_base_shape_native_hotpath_calls")) or 0) == 0,
              f"{rid}: q31 hotpath calls == 0")
        if rid.startswith("S") or (rid.startswith("E") and ai(r.get("spacing_mm") or 0)):
            check((ai(r.get("technology_spacing_offset_failure_count")) or 0) == 0,
                  f"{rid}: spacing offset_failure_count == 0")

    # Renders present per used sheet + overview.
    for rid in runs:
        r = summary.get(rid)
        if not r:
            continue
        used = ai(r.get("used_sheet_count")) or 0
        rdir = RENDERS / rid
        ok_renders = True
        for i in range(used):
            if not (rdir / f"sheet_{i:02d}.svg").exists() or not (rdir / f"sheet_{i:02d}.png").exists():
                ok_renders = False
        if not (rdir / "overview.svg").exists() or not (rdir / "overview.png").exists():
            ok_renders = False
        check(ok_renders, f"{rid}: SVG+PNG per used sheet ({used}) + overview present")

    # Regression gates.
    gp = TABLES / "q39_regression_gates.json"
    if gp.exists():
        g = json.loads(gp.read_text())
        for k in ("dense191_baseline_ok", "full276_2sheet_baseline_ok", "full276_3sheet_baseline_ok",
                  "mixed_stock_baseline_valid", "mandatory_spacing_runs_valid",
                  "all_mandatory_renders_present", "no_false_ok", "hotpath_calls_zero"):
            check(g.get(k) is True, f"regression gate {k} == true (got {g.get(k)})")
        check(g.get("time_limit_cap_applied") is False, "time_limit_cap_applied == false (no mandatory cap)")

    # Manifest: no errors, no cap.
    mp = TABLES / "q39_measurement_manifest.json"
    if mp.exists():
        m = json.loads(mp.read_text())
        check(not m.get("errors"), f"manifest reports no errors ({m.get('errors')})")
        check(m.get("time_limit_cap_applied") is False, "manifest: no time-limit cap")

    print(f"\n{'='*52}\n  PASS: {PASS}   FAIL: {FAIL}")
    if FAIL:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
