#!/usr/bin/env python3
"""SGH-Q24R1 native Sparrow parity lifecycle benchmark — LV8 ladder.

Adds per-target-search CDE session reuse metrics (builds/reuses/ratio).

Measures production `sparrow_cde` (CDE backend) across:
  medium_10_to_20_items, lv8_12types_x1, lv8_24_instances,
  lv8_50_instances, lv8_100_instances (--full), lv8_full_276 (--full).

LV8 subsets are OUTER-ONLY (holes stripped — the Phase1/sparrow_cde path is
outer-only). Every production run counts in the denominator
(ok/partial/unsupported/timeout/error). Larger rows may time out; that is
measured honestly, not skipped.

Assumptions (also in the report): sheet = LV8 fixture sheet (1500x3000),
sheet_qty scales with row, seed=11, rotation=orthogonal, backend=cde,
pipeline=sparrow_cde, per-run wall cap as configured below.

Outputs:
  codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.json
  codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.md
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
LV8_FIXTURE = ROOT / "tests" / "fixtures" / "nesting_engine" / "ne2_input_lv8jav.json"
PROFILE = "jagua_optimizer_phase1_outer_only"
REPORT_DIR = ROOT / "codex" / "reports" / "egyedi_solver"
STEM = "sgh_q24r1_native_sparrow_parity_lifecycle_measurements"


def run_solver(inp, hard_timeout_s):
    with tempfile.TemporaryDirectory() as d:
        ip = Path(d) / "in.json"
        op = Path(d) / "out.json"
        ip.write_text(json.dumps(inp))
        t0 = time.perf_counter()
        try:
            r = subprocess.run([str(BINARY), "--input", str(ip), "--output", str(op)],
                               capture_output=True, text=True, timeout=hard_timeout_s)
        except subprocess.TimeoutExpired:
            return ({"status": "timeout"}, (time.perf_counter() - t0) * 1000.0)
        ms = (time.perf_counter() - t0) * 1000.0
        if r.returncode != 0:
            return ({"status": "error", "stderr": r.stderr[:200]}, ms)
        return (json.loads(op.read_text()), ms)


def lv8_types():
    data = json.loads(LV8_FIXTURE.read_text())
    sheet = data.get("sheet") or {}
    types = []
    for p in data.get("parts", []):
        pts = p.get("outer_points_mm") or []
        if not pts:
            continue
        xs = [float(a[0]) for a in pts]
        ys = [float(a[1]) for a in pts]
        types.append({"id": p["id"], "quantity": int(p.get("quantity", 1)),
                      "width": max(xs) - min(xs), "height": max(ys) - min(ys),
                      "allowed_rotations_deg": p.get("allowed_rotations_deg", [0, 90, 180, 270]),
                      "outer_points": pts})
    return sheet, types


def lv8_input(spec, name, sheet_qty, tl):
    sheet, types = lv8_types()
    if not types:
        return None, 0
    if spec == "12types":
        parts = [dict(t, quantity=1) for t in types]
    else:
        n = int(spec)
        caps = {t["id"]: t["quantity"] for t in types}
        used = {t["id"]: 0 for t in types}
        chosen = []
        idx = 0
        while len(chosen) < n and idx < 1000000:
            t = types[idx % len(types)]
            if used[t["id"]] < caps[t["id"]]:
                chosen.append(t["id"]); used[t["id"]] += 1
            idx += 1
        c = Counter(chosen)
        parts = [dict(next(t for t in types if t["id"] == i), quantity=q) for i, q in c.items()]
    req = sum(p["quantity"] for p in parts)
    inp = {"contract_version": "v1", "project_name": name, "seed": 11, "time_limit_s": tl,
           "solver_profile": PROFILE, "optimizer_pipeline": "sparrow_cde",
           "collision_backend": "cde", "rotation_policy": "orthogonal",
           "stocks": [{"id": "LV8_SHEET", "quantity": sheet_qty,
                       "width": float(sheet.get("width_mm", 1500.0)),
                       "height": float(sheet.get("height_mm", 3000.0))}],
           "parts": parts}
    return inp, req


def medium_input():
    return ({"contract_version": "v1", "project_name": "q24_medium", "seed": 5, "time_limit_s": 8,
             "solver_profile": PROFILE, "optimizer_pipeline": "sparrow_cde",
             "collision_backend": "cde", "rotation_policy": "orthogonal",
             "stocks": [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
             "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}]}, 12)


def summarize(name, hard, inp, req, out, ms):
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    return {
        "row": name, "hard_gate": hard, "required": req,
        "status": out.get("status"), "runtime_ms": round(ms, 1),
        "placed": (out.get("metrics") or {}).get("placed_count"),
        "converged": od.get("sparrow_converged"),
        "final_pairs": od.get("sparrow_collision_graph_final_pairs"),
        "loss_model_used": od.get("loss_model_used"),
        "loss_bbox_primary": od.get("loss_bbox_proxy_used_as_primary"),
        "search_calls": od.get("sparrow_search_position_calls"),
        "search_samples": od.get("sparrow_search_position_samples"),
        "backend_used": cbd.get("backend_used"),
        "bbox_fallback": cbd.get("bbox_fallback_queries"),
        "lbf_fallback": od.get("search_position_lbf_fallback_used"),
        "cde_batch_engine_builds": cbd.get("cde_batch_engine_builds"),
        "session_builds": cbd.get("cde_candidate_session_builds"),
        "session_reuses": cbd.get("cde_candidate_session_reuses"),
        "pairwise_fallback": cbd.get("cde_pairwise_fallback_queries"),
    }


def rv(v):
    return "-" if v is None else v


def emit_md(rows, acct):
    L = ["# SGH-Q24R1 native Sparrow parity lifecycle — LV8 ladder measurements\n",
         "Production `sparrow_cde` + CDE backend. LV8 subsets are OUTER-ONLY (holes stripped).",
         "Assumptions: sheet 1500x3000 (LV8 fixture), seed 11, rotation orthogonal, "
         "pipeline sparrow_cde, backend cde. Every production run counts in the denominator.\n",
         "| row | hard | status | placed/req | conv | final_pairs | runtime_ms | loss_model | bbox_primary | search_samples | bbox_fb | lbf_fb |",
         "|---|---|---|---|---|---:|---:|---|---|---:|---:|---:|"]
    for r in rows:
        L.append(f"| {r['row']} | {'Y' if r['hard_gate'] else 'n'} | {r['status']} | "
                 f"{rv(r['placed'])}/{r['required']} | {rv(r['converged'])} | {rv(r['final_pairs'])} | "
                 f"{r['runtime_ms']} | {rv(r['loss_model_used'])} | {rv(r['loss_bbox_primary'])} | "
                 f"{rv(r['search_samples'])} | {rv(r['bbox_fallback'])} | {rv(r['lbf_fallback'])} |")
    L.append("\n## Outcome accounting (all production rows)\n")
    L.append("| outcome | count |\n|---|---:|")
    for k in ("ok", "partial", "unsupported", "timeout", "error"):
        L.append(f"| {k} | {acct.get(k, 0)} |")
    L.append(f"| **total** | **{acct['total']}** |")
    L.append(f"| **hard gates passed** | **{acct['hard_passed']}/{acct['hard_total']}** |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        sys.exit(1)

    # (name, hard_gate, builder)
    plan = [
        ("medium_10_to_20_items", True, lambda: medium_input(), 60.0),
        ("lv8_12types_x1", True, lambda: lv8_input("12types", "lv8_12types_x1", 4, 8), 35.0),
        ("lv8_24_instances", True, lambda: lv8_input("24", "lv8_24_instances", 6, 8), 35.0),
        ("lv8_50_instances", False, lambda: lv8_input("50", "lv8_50_instances", 8, 10), 45.0),
    ]
    if args.full:
        plan += [
            ("lv8_100_instances", False, lambda: lv8_input("100", "lv8_100_instances", 12, 12), 60.0),
            ("lv8_full_276", False, lambda: lv8_input("276", "lv8_full_276", 24, 15), 90.0),
        ]

    rows = []
    acct = {"ok": 0, "partial": 0, "unsupported": 0, "timeout": 0, "error": 0,
            "total": 0, "hard_passed": 0, "hard_total": 0}
    for name, hard, builder, cap in plan:
        built = builder()
        inp, req = built if isinstance(built, tuple) else (built, 0)
        if inp is None:
            print(f"[skip] {name}: LV8 fixture missing")
            continue
        print(f"[run] {name} (hard={hard}, cap={cap}s)", flush=True)
        out, ms = run_solver(inp, hard_timeout_s=cap)
        r = summarize(name, hard, inp, req, out, ms)
        rows.append(r)
        acct["total"] += 1
        st = r["status"] if r["status"] in acct else "error"
        acct[st] = acct.get(st, 0) + 1
        if hard:
            acct["hard_total"] += 1
            if r["status"] == "ok" and r["placed"] == req and (r["final_pairs"] or 0) == 0:
                acct["hard_passed"] += 1
        print(f"      -> status={r['status']} placed={rv(r['placed'])}/{req} "
              f"conv={rv(r['converged'])} {r['runtime_ms']}ms")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{STEM}.json").write_text(json.dumps({"rows": rows, "accounting": acct}, indent=2))
    (REPORT_DIR / f"{STEM}.md").write_text(emit_md(rows, acct))
    print(f"\n[done] wrote {REPORT_DIR / (STEM + '.json')}")
    print(f"[done] hard gates passed {acct['hard_passed']}/{acct['hard_total']}; total rows {acct['total']}")


if __name__ == "__main__":
    main()
