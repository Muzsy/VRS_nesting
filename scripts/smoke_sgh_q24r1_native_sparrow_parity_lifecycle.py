#!/usr/bin/env python3
"""SGH-Q24R1 native Sparrow parity lifecycle smoke.

Production `sparrow_cde` hard gates (smoke exits non-zero on any failure):
  - medium_10_to_20_items: ok 12/12, pairs 0, no fallback;
  - production loss_model_used != bbox/PolePenetration, bbox proxy not primary;
  - CDE session reuse active: cde_session_reuse_ratio >= 0.80, pairwise_fallback == 0
    (SGH-Q24R1 #2 — per-target-search session reuse);
  - lv8_12types_x1: ok 12/12 within wall cap;
  - lv8_24_instances: ok 24/24 within wall cap.

LV8 subsets are OUTER-ONLY (holes stripped; Phase1/sparrow_cde is outer-only).

Honest status: the LV8 12-types/24 hard gates currently TIME OUT — the cost is
query-bound (collect_poly_collisions over large real polygons × separation-probe
volume), which per-target-search session reuse alone does not remove. This smoke
reports that failure truthfully.
"""

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

PASS_COUNT = 0
FAIL_COUNT = 0


def _log(label, msg):
    print(f"  [{label}] {msg}")


def check(cond, msg):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        _log("PASS", msg)
    else:
        FAIL_COUNT += 1
        _log("FAIL", msg)


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


def reuse_ratio(cbd):
    b = cbd.get("cde_candidate_session_builds") or 0
    r = cbd.get("cde_candidate_session_reuses") or 0
    return (r / (r + b)) if (r + b) > 0 else 0.0


def lv8_input(spec, name, sheet_qty, tl=8):
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
        while len(chosen) < n and idx < 100000:
            t = types[idx % len(types)]
            if used[t["id"]] < caps[t["id"]]:
                chosen.append(t["id"]); used[t["id"]] += 1
            idx += 1
        c = Counter(chosen)
        parts = [dict(next(t for t in types if t["id"] == i), quantity=q) for i, q in c.items()]
    req = sum(p["quantity"] for p in parts)
    return ({"contract_version": "v1", "project_name": name, "seed": 11, "time_limit_s": tl,
             "solver_profile": PROFILE, "optimizer_pipeline": "sparrow_cde",
             "collision_backend": "cde", "rotation_policy": "orthogonal",
             "stocks": [{"id": "LV8_SHEET", "quantity": sheet_qty,
                         "width": float(sheet.get("width_mm", 1500.0)),
                         "height": float(sheet.get("height_mm", 3000.0))}],
             "parts": parts}, req)


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        sys.exit(1)
    print("SGH-Q24R1 native Sparrow parity lifecycle smoke")

    # ── medium hard gate + session reuse + loss identity ─────────────────────
    print("\n=== medium_10_to_20_items (hard) ===")
    medium = {"contract_version": "v1", "project_name": "q24r1_medium", "seed": 5, "time_limit_s": 8,
              "solver_profile": PROFILE, "optimizer_pipeline": "sparrow_cde", "collision_backend": "cde",
              "rotation_policy": "orthogonal",
              "stocks": [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
              "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}]}
    out, ms = run_solver(medium, hard_timeout_s=60.0)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") == "ok", f"medium ok ({out.get('status')}, {ms/1000:.1f}s)")
    check((out.get("metrics") or {}).get("placed_count") == 12, "medium 12/12")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, "medium final pairs 0")
    check(od.get("loss_model_used") not in (None, "BboxAreaLoss", "PolePenetrationSmoothLoss"),
          f"loss_model_used CDE-driven (got {od.get('loss_model_used')})")
    check(od.get("loss_bbox_proxy_used_as_primary") is False, "bbox proxy not primary")
    rr = reuse_ratio(cbd)
    _log("INFO", f"medium session builds={cbd.get('cde_candidate_session_builds')} "
                 f"reuses={cbd.get('cde_candidate_session_reuses')} reuse_ratio={rr:.3f}")
    check(rr >= 0.80, f"CDE session reuse_ratio >= 0.80 (got {rr:.3f})")
    check((cbd.get("cde_pairwise_fallback_queries") or 0) == 0, "no CDE pairwise fallback")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback")
    check((od.get("search_position_lbf_fallback_used") or 0) == 0, "no LBF fallback")
    check(cbd.get("backend_used") == "cde_adapter", "CDE backend")

    # ── LV8 hard gates ───────────────────────────────────────────────────────
    for spec, req_expected, cap, sheet_qty, label in [
        ("12types", 12, 60.0, 4, "lv8_12types_x1"),
        ("24", 24, 90.0, 6, "lv8_24_instances"),
    ]:
        print(f"\n=== {label} (hard) ===")
        inp, req = lv8_input(spec, label, sheet_qty)
        if inp is None:
            check(False, "LV8 fixture missing/empty")
            continue
        out, ms = run_solver(inp, hard_timeout_s=cap)
        placed = (out.get("metrics") or {}).get("placed_count")
        _log("INFO", f"{label} status={out.get('status')} placed={placed}/{req} {ms/1000:.1f}s")
        check(out.get("status") == "ok" and placed == req == req_expected,
              f"{label} ok {req_expected}/{req_expected} (got status={out.get('status')} placed={placed}/{req})")

    print("\n" + "=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL (Q24R1 hard gates include LV8 12-types/24 convergence)")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
