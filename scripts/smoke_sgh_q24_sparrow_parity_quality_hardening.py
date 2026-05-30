#!/usr/bin/env python3
"""SGH-Q24 Sparrow parity quality hardening smoke.

Production `sparrow_cde` quality gates. HARD gates (smoke exits non-zero on fail):
  - medium_10_to_20_items stays ok 12/12, pairs 0, no fallback;
  - production loss_model_used != bbox_area, bbox proxy not primary;
  - production search budget is non-trivial (search samples > 0);
  - exploration + compression diagnostics present;
  - lv8_12types_x1 ok 12/12 within wall cap;
  - lv8_24_instances ok 24/24 within wall cap.

LV8 subsets are OUTER-ONLY (holes stripped): the Phase1/sparrow_cde path is
outer-only and rejects hole geometry, and only 3 of 12 LV8 types are hole-free.
The 12-type / 24-instance hard gates therefore use each type's outer boundary.

Honest note: the LV8 hard gates currently TIME OUT on real irregular geometry
(the per-candidate CDE session cost does not yet scale to 12+ large polygons).
This smoke reports that failure truthfully (it does not skip LV8).
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
LV8_FIXTURE = ROOT / "tests" / "fixtures" / "nesting_engine" / "ne2_input_lv8jav.json"
PROFILE = "jagua_optimizer_phase1_outer_only"
LV8_WALL_CAP_S = 35.0

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


def run_solver(inp, hard_timeout_s=40.0):
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


def base_input(parts, stocks, seed=0, rotation="orthogonal", tl=8):
    return {
        "contract_version": "v1", "project_name": "q24_smoke", "seed": seed,
        "time_limit_s": tl, "solver_profile": PROFILE,
        "optimizer_pipeline": "sparrow_cde", "collision_backend": "cde",
        "rotation_policy": rotation, "stocks": stocks, "parts": parts,
    }


def lv8_types(outer_only=True):
    """All LV8 part types as outer-only parts (holes stripped)."""
    data = json.loads(LV8_FIXTURE.read_text())
    sheet = data.get("sheet") or {}
    types = []
    for p in data.get("parts", []):
        pts = p.get("outer_points_mm") or []
        if not pts:
            continue
        xs = [float(a[0]) for a in pts]
        ys = [float(a[1]) for a in pts]
        types.append({
            "id": p["id"], "quantity": int(p.get("quantity", 1)),
            "width": max(xs) - min(xs), "height": max(ys) - min(ys),
            "allowed_rotations_deg": p.get("allowed_rotations_deg", [0, 90, 180, 270]),
            "outer_points": pts,
        })
    return sheet, types


def lv8_input(target_instances, name, sheet_qty=4, tl=8):
    sheet, types = lv8_types()
    if not types:
        return None
    if target_instances == "12types":
        parts = [dict(t, quantity=1) for t in types]
    else:
        n = int(target_instances)
        caps = {t["id"]: t["quantity"] for t in types}
        used = {t["id"]: 0 for t in types}
        chosen = []
        idx = 0
        while len(chosen) < n and idx < 100000:
            t = types[idx % len(types)]
            if used[t["id"]] < caps[t["id"]]:
                chosen.append(t["id"])
                used[t["id"]] += 1
            idx += 1
        from collections import Counter
        c = Counter(chosen)
        parts = [dict(next(t for t in types if t["id"] == i), quantity=q) for i, q in c.items()]
    return {
        "contract_version": "v1", "project_name": name, "seed": 11, "time_limit_s": tl,
        "solver_profile": PROFILE, "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde", "rotation_policy": "orthogonal",
        "stocks": [{"id": "LV8_SHEET", "quantity": sheet_qty,
                    "width": float(sheet.get("width_mm", 1500.0)),
                    "height": float(sheet.get("height_mm", 3000.0))}],
        "parts": parts,
    }


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        sys.exit(1)
    print("SGH-Q24 Sparrow parity quality hardening smoke")

    # ── medium hard gate + production quality gates ──────────────────────────
    print("\n=== medium_10_to_20_items (hard) ===")
    out, ms = run_solver(base_input(
        [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}], seed=5, tl=8),
        hard_timeout_s=60.0)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    check(out.get("status") == "ok", f"medium ok (got {out.get('status')}, {ms/1000:.1f}s)")
    placed = (out.get("metrics") or {}).get("placed_count")
    check(placed == 12, f"medium 12/12 (got {placed})")
    check(od.get("sparrow_converged") is True, "medium converged")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, "medium final pairs 0")
    # D: production loss model
    check(od.get("loss_model_used") not in (None, "BboxAreaLoss"),
          f"loss_model_used != bbox_area (got {od.get('loss_model_used')})")
    check(od.get("loss_bbox_proxy_used_as_primary") is False,
          f"bbox proxy not primary (got {od.get('loss_bbox_proxy_used_as_primary')})")
    # A: non-trivial search
    check((od.get("sparrow_search_position_samples") or 0) > 0,
          f"non-trivial search samples (got {od.get('sparrow_search_position_samples')})")
    check((od.get("sparrow_search_position_calls") or 0) > 0, "search_position calls > 0")
    # no fallback
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback")
    check((od.get("search_position_lbf_fallback_used") or 0) == 0, "no LBF fallback")
    check(cbd.get("backend_used") == "cde_adapter", "CDE backend")
    # exploration + compression diagnostics present (Q23R3 lifecycle)
    check(od.get("sparrow_exploration_restarts") is not None
          or od.get("sparrow_restarts") is not None, "exploration diagnostics present")
    check(od.get("sparrow_compression_passes") is not None
          or od.get("sparrow_compression_accepts") is not None
          or od.get("sparrow_fixed_sheet_objective_before") is not None,
          "compression diagnostics present")

    # ── LV8 12-types-x1 hard gate ────────────────────────────────────────────
    print("\n=== lv8_12types_x1 (hard) ===")
    inp = lv8_input("12types", "lv8_12types_x1")
    if inp is None:
        check(False, "LV8 fixture missing/empty")
    else:
        req = sum(p["quantity"] for p in inp["parts"])
        out, ms = run_solver(inp, hard_timeout_s=LV8_WALL_CAP_S)
        od = out.get("optimizer_diagnostics") or {}
        placed = (out.get("metrics") or {}).get("placed_count")
        _log("INFO", f"lv8_12types status={out.get('status')} placed={placed}/{req} {ms/1000:.1f}s")
        check(out.get("status") == "ok" and placed == req and req == 12,
              f"lv8_12types_x1 ok 12/12 (got status={out.get('status')} placed={placed}/{req})")

    # ── LV8 24-instance hard gate ────────────────────────────────────────────
    print("\n=== lv8_24_instances (hard) ===")
    inp = lv8_input("24", "lv8_24_instances")
    if inp is None:
        check(False, "LV8 fixture missing/empty")
    else:
        req = sum(p["quantity"] for p in inp["parts"])
        out, ms = run_solver(inp, hard_timeout_s=LV8_WALL_CAP_S)
        placed = (out.get("metrics") or {}).get("placed_count")
        _log("INFO", f"lv8_24 status={out.get('status')} placed={placed}/{req} {ms/1000:.1f}s")
        check(out.get("status") == "ok" and placed == req and req == 24,
              f"lv8_24_instances ok 24/24 (got status={out.get('status')} placed={placed}/{req})")

    print("\n" + "=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL (Q24 hard gates include LV8 12-types/24 convergence)")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
