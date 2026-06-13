#!/usr/bin/env python3
"""SGH-Q41 smoke — validate the full276 margin 5 / spacing 10 visual benchmark under Q40.

Validates the artifacts produced by
`bench_sgh_q41_full276_m5_s10_visuals.py --tier mandatory` (run that first). Does NOT re-run
the heavy 3×1200 s solver matrix.

Static checks: bench script + report + artifact dirs + required tables + render dirs exist;
the runner declares EXACTLY 3 full276 scenarios at margin=5 / spacing=10 (no dense191, no
spacing=2), uses the canonical full276 input, reuses the Q39 render logic, and never enables
the Q35 spacing validator by default.

Dynamic checks: all three outputs parse; each run is 276-instance full276 at margin=5 /
spacing=10 with offset_mm=5, solver_sheet_inset=0, inner_spacing=0, offset_failure=0,
final_pairs=0, boundary=0, margin_viol=0; ok ⇒ unplaced=0, partial ⇒ exact unplaced list;
SVG+PNG per used sheet + overview present; every mandatory regression gate true.

Exit codes: 0 PASS, 2 FAIL.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q41 = ROOT / "artifacts/benchmarks/sgh_q41"
TABLES = Q41 / "tables"
RENDERS = Q41 / "renders"
OUTPUTS = Q41 / "outputs"
BENCH = ROOT / "scripts/bench_sgh_q41_full276_m5_s10_visuals.py"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q41_full276_m5_s10_visual_benchmark.md"
ADAPTER = ROOT / "rust/vrs_solver/src/adapter.rs"

RUN_IDS = ["Q41_A_2L", "Q41_B_3L", "Q41_C_MIXED"]
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


def af(v):
    try:
        return float(v)
    except Exception:
        return None


def load_bench_module():
    spec = importlib.util.spec_from_file_location("q41bench", BENCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    print("=== SGH-Q41 full276 m5/s10 visual benchmark smoke ===")
    print("\n--- Static checks ---")
    check(BENCH.exists(), "bench_sgh_q41_full276_m5_s10_visuals.py exists")
    for d in ("inputs", "outputs", "tables", "logs", "renders"):
        check((Q41 / d).exists(), f"artifact dir exists: {d}")
    for t in ("q41_run_summary.csv", "q41_per_sheet_summary.csv", "q41_stage_timing.csv",
              "q41_cde_metrics.csv", "q41_render_summary.csv",
              "q41_regression_gates.json", "q41_measurement_manifest.json"):
        check((TABLES / t).exists(), f"table exists: {t}")
    check(REPORT.exists(), "Q41 report exists")
    if REPORT.exists():
        rep = REPORT.read_text()
        for sec in ("## Scope", "## Margin 5 / spacing 10 interpretation",
                    "## Recommended next task", "## Final verdict"):
            check(sec in rep, f"report has '{sec}'")

    # Structural checks via import (robust against docstring text mentioning dense191/spacing 2).
    try:
        mod = load_bench_module()
    except Exception as e:
        check(False, f"bench module imports cleanly ({e})")
        mod = None
    if mod is not None:
        scns = list(getattr(mod, "SCENARIOS", []))
        check(len(scns) == 3, f"runner declares exactly 3 scenarios (got {len(scns)})")
        check(all(abs(float(s[3]) - 5.0) < 1e-9 for s in scns), "every scenario margin == 5")
        check(all(abs(float(s[4]) - 10.0) < 1e-9 for s in scns), "every scenario spacing == 10")
        check(not any(abs(float(s[4]) - 2.0) < 1e-9 for s in scns), "no scenario uses spacing == 2")
        check(all(int(s[5]) == 1200 for s in scns), "every scenario uses the full 1200 s time limit")
        check(getattr(mod, "BASE_FULL276", Path()).name == "case_01_2x1500x3000.json",
              "runner uses the canonical full276 input")
        check(getattr(mod, "BASE_DENSE191", None) is None
              and not any("dense" in str(s).lower() for s in scns),
              "no dense191 scenario in the runner")
        # Reuses Q39 render logic (adapted): the same render helpers are present.
        for fn in ("render_sheet_svg", "render_overview_svg", "_transform", "part_polygon_area"):
            check(hasattr(mod, fn), f"runner reuses Q39 render helper: {fn}")
        # Runner forces the Q35 spacing validator OFF by default (never inherits the env flag).
        src = BENCH.read_text()
        check("SGH_Q35_SPACING_VALIDATOR" in src and ".pop(\"SGH_Q35_SPACING_VALIDATOR\"" in src,
              "runner forces Q35 spacing validator disabled (env popped)")

    # Adapter still keeps the Q35 validator env-gated (default disabled).
    if ADAPTER.exists():
        a = ADAPTER.read_text()
        check("SGH_Q35_SPACING_VALIDATOR" in a and "spacing_validator_enabled" in a,
              "adapter.rs: Q35 spacing validator is env-gated (default disabled)")

    summary = {}
    sp = TABLES / "q41_run_summary.csv"
    if sp.exists() and sp.read_text().strip():
        summary = {r["run_id"]: r for r in csv.DictReader(sp.open())}

    print("\n--- Dynamic checks ---")
    check(set(summary.keys()) == set(RUN_IDS), f"run_summary has exactly the 3 Q41 runs ({sorted(summary)})")

    for rid in RUN_IDS:
        r = summary.get(rid)
        if not r:
            check(False, f"{rid}: present in run_summary")
            continue
        # Output parseable + exact unplaced reporting.
        out_path = OUTPUTS / f"{rid}_output.json"
        out = None
        if out_path.exists():
            try:
                out = json.loads(out_path.read_text())
                check(True, f"{rid}: output JSON parseable")
            except Exception as e:
                check(False, f"{rid}: output JSON parseable ({e})")
        else:
            check(False, f"{rid}: output JSON exists")

        check(ai(r.get("total_instances")) == 276, f"{rid}: total_instances == 276")
        check(af(r.get("margin_mm")) == 5.0, f"{rid}: margin_mm == 5")
        check(af(r.get("spacing_mm")) == 10.0, f"{rid}: spacing_mm == 10")
        check(af(r.get("kerf_mm")) == 0.0, f"{rid}: kerf_mm == 0")
        check(af(r.get("technology_spacing_offset_mm")) == 5.0, f"{rid}: spacing_offset_mm == 5")
        # Optional fields (present in this build): inset == 0, inner spacing == 0.
        inset = af(r.get("technology_solver_sheet_inset_mm"))
        check(inset is None or abs(inset) < 1e-9, f"{rid}: solver_sheet_inset_mm == 0 (got {r.get('technology_solver_sheet_inset_mm')})")
        inner = af(r.get("technology_inner_spacing_mm"))
        check(inner is None or abs(inner) < 1e-9, f"{rid}: inner_spacing_mm == 0 (got {r.get('technology_inner_spacing_mm')})")
        check(str(r.get("technology_unified_geometry_model_active")).lower() == "true",
              f"{rid}: unified_geometry_model_active == true")
        check((ai(r.get("technology_spacing_offset_failure_count")) or 0) == 0,
              f"{rid}: spacing_offset_failure_count == 0")
        check((ai(r.get("final_pairs")) or 0) == 0, f"{rid}: final_pairs == 0")
        check((ai(r.get("boundary_violations")) or 0) == 0, f"{rid}: boundary_violations == 0")
        check((ai(r.get("technology_margin_violation_count")) or 0) == 0,
              f"{rid}: margin_violation_count == 0")
        check((ai(r.get("q31_prepare_base_shape_native_hotpath_calls")) or 0) == 0,
              f"{rid}: q31 hotpath calls == 0")

        status = r.get("status")
        placed = ai(r.get("placed_count")) or 0
        unplaced = ai(r.get("unplaced_count")) or 0
        if status == "ok":
            check(placed == 276 and unplaced == 0, f"{rid}: status ok ⇒ 276/0")
        else:
            check(status == "partial", f"{rid}: non-ok status is partial (got {status!r})")
            check(unplaced > 0, f"{rid}: partial ⇒ unplaced_count > 0 (got {unplaced})")
            if out is not None:
                ul = out.get("unplaced", [])
                exact = (len(ul) == unplaced
                         and all(u.get("instance_id") and u.get("part_id") and u.get("reason") for u in ul))
                check(exact, f"{rid}: exact unplaced list (len {len(ul)} == {unplaced}, all fields set)")

        # Renders: SVG+PNG per used sheet + overview.
        used = ai(r.get("render_sheet_count")) or 0
        rdir = RENDERS / rid
        ok_renders = True
        for i in range(used):
            if not (rdir / f"sheet_{i:02d}.svg").exists() or not (rdir / f"sheet_{i:02d}.png").exists():
                ok_renders = False
        if not (rdir / "overview.svg").exists() or not (rdir / "overview.png").exists():
            ok_renders = False
        check(ok_renders, f"{rid}: SVG+PNG per used sheet ({used}) + overview present")

    # Regression gates: every mandatory gate true.
    gp = TABLES / "q41_regression_gates.json"
    if gp.exists():
        g = json.loads(gp.read_text())
        for k in ("all_three_runs_completed", "all_inputs_full276", "all_runs_margin_5_spacing_10",
                  "all_runs_full_time_limit", "q40_unified_model_active", "solver_sheet_inset_zero",
                  "inner_spacing_zero", "offset_mm_is_5", "offset_failure_zero", "no_false_ok",
                  "no_final_collisions", "no_boundary_violations", "no_margin_violations",
                  "hotpath_calls_zero", "spacing_validator_disabled_by_default",
                  "all_renders_present", "render_original_contours"):
            check(g.get(k) is True, f"regression gate {k} == true (got {g.get(k)})")

    print(f"\n{'=' * 52}\n  PASS: {PASS}   FAIL: {FAIL}")
    if FAIL:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
