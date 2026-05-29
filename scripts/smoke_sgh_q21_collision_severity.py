#!/usr/bin/env python3
"""SGH-Q21 CDE/Sparrow collision severity + evaluate_transform smoke script.

Fixtures:
  1. jagua_polygon_exact — severity engine fires (boundary_queries > 0), no bbox proxy
  2. Bbox backend — severity engine bypassed entirely (all oracle stats zero)
  3. CDE path — no bbox proxy, severity engine fires, bbox_fallback_queries == 0
  4. Backend name wired into diagnostics — collision_severity_backend matches input backend
  5. All 9 collision_severity fields present in optimizer_diagnostics output

Design: use a large-sheet / low-density fixture with continuous rotation so that
rotation refinement creates transient overlaps that search_position must resolve via
the oracle backend.  Oracle probes resolve in 1–2 steps on large sheets → fast.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BINARY = Path(__file__).parent.parent / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"

PASS_COUNT = 0
FAIL_COUNT = 0


def _log(label: str, msg: str):
    print(f"  [{label}] {msg}")


def check(cond: bool, msg: str):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        _log("PASS", msg)
    else:
        FAIL_COUNT += 1
        _log("FAIL", msg)


def run_solver(input_dict: dict, seed: int = 0) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "in.json"
        out_path = Path(tmpdir) / "out.json"
        in_path.write_text(json.dumps(input_dict))
        result = subprocess.run(
            [str(BINARY), "--input", str(in_path), "--output", str(out_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  [ERROR] solver exited {result.returncode}: {result.stderr[:300]}")
            return {}
        return json.loads(out_path.read_text())


def base_input(backend: str | None = None, time_limit: int = 5) -> dict:
    """Large-sheet low-density fixture with continuous rotation.

    Continuous rotation generates transient overlaps that search_position resolves;
    oracle probes on a large sheet resolve in 1–2 steps → fast.
    """
    inp: dict = {
        "contract_version": "v1",
        "project_name": "q21_smoke",
        "seed": 0,
        "time_limit_s": time_limit,
        "solver_profile": PROFILE,
        "optimizer_pipeline": "phase_optimizer",
        "rotation_policy": "continuous",
        "stocks": [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 4}],
    }
    if backend:
        inp["collision_backend"] = backend
    return inp


# ---------------------------------------------------------------------------


def fixture1_exact_backend_severity_engine():
    print("\n=== Fixture 1: jagua_polygon_exact — severity engine fires, no bbox proxy ===")
    out = run_solver(base_input(backend="jagua_polygon_exact"))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        enabled = od.get("collision_severity_enabled", False)
        check(enabled, f"collision_severity_enabled == true (got {enabled})")
        # boundary_queries > 0 whenever eval_at_point fires (checks boundary first).
        bdry_q = od.get("collision_severity_boundary_queries", 0)
        check(bdry_q > 0,
              f"collision_severity_boundary_queries > 0 (got {bdry_q})")
        bbox_proxy = od.get("collision_severity_bbox_proxy_uses", -1)
        check(bbox_proxy == 0,
              f"collision_severity_bbox_proxy_uses == 0 with exact backend (got {bbox_proxy})")
        backend_str = od.get("collision_severity_backend", "")
        check("JaguaPolygonExact" in backend_str,
              f"collision_severity_backend contains 'JaguaPolygonExact' (got '{backend_str}')")
        sp_calls = od.get("search_position_calls", 0)
        check(sp_calls > 0, f"search_position_calls > 0 (got {sp_calls})")
        _log("INFO", f"sp_calls={sp_calls} bdry_q={bdry_q} bbox_proxy={bbox_proxy} "
                     f"pair_q={od.get('collision_severity_pair_queries')} "
                     f"probe_q={od.get('collision_severity_probe_queries')} "
                     f"conf_coll={od.get('collision_severity_backend_confirmed_collisions')}")


def fixture2_bbox_backend_bypasses_severity_engine():
    print("\n=== Fixture 2: Bbox backend — severity engine bypassed (all oracle stats zero) ===")
    # With Bbox backend, evaluate_transform_loss takes the early-exit path via eval_bbox_loss,
    # which skips the severity engine entirely — all CollisionSeverityStats remain zero.
    out = run_solver(base_input(backend=None))
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        backend_str = od.get("collision_severity_backend", "")
        check("Bbox" in backend_str,
              f"collision_severity_backend contains 'Bbox' (got '{backend_str}')")
        pair_q = od.get("collision_severity_pair_queries", -1)
        bdry_q = od.get("collision_severity_boundary_queries", -1)
        bbox_proxy = od.get("collision_severity_bbox_proxy_uses", -1)
        check(pair_q == 0,
              f"pair_queries == 0 with bbox (early-exit bypasses oracle, got {pair_q})")
        check(bdry_q == 0,
              f"boundary_queries == 0 with bbox (early-exit bypasses oracle, got {bdry_q})")
        check(bbox_proxy == 0,
              f"bbox_proxy_uses == 0 with bbox (not the oracle path, got {bbox_proxy})")
        sp_calls = od.get("search_position_calls", 0)
        check(sp_calls > 0, f"search_position_calls > 0 (solver is active, got {sp_calls})")
        _log("INFO", f"sp_calls={sp_calls} pair_q={pair_q} bdry_q={bdry_q} bbox_proxy={bbox_proxy}")


def fixture3_cde_path_no_bbox_proxy():
    print("\n=== Fixture 3: CDE path — severity engine fires, no bbox proxy ===")
    out = run_solver(base_input(backend="cde"))
    check(out.get("status") in ("ok", "partial", "unsupported"),
          f"status ok/partial/unsupported (got {out.get('status')})")
    if out.get("status") == "unsupported":
        _log("SKIP", "CDE returned unsupported — skip remaining CDE checks")
        return
    cbd = out.get("collision_backend_diagnostics")
    check(cbd is not None, "collision_backend_diagnostics present")
    if cbd:
        fallback = cbd.get("bbox_fallback_queries", -1)
        check(fallback == 0, f"bbox_fallback_queries == 0 (got {fallback})")
    od = out.get("optimizer_diagnostics")
    check(od is not None, "optimizer_diagnostics present")
    if od:
        bbox_proxy = od.get("collision_severity_bbox_proxy_uses", -1)
        check(bbox_proxy == 0,
              f"collision_severity_bbox_proxy_uses == 0 with CDE (got {bbox_proxy})")
        backend_str = od.get("collision_severity_backend", "")
        check("Cde" in backend_str,
              f"collision_severity_backend contains 'Cde' (got '{backend_str}')")
        bdry_q = od.get("collision_severity_boundary_queries", 0)
        check(bdry_q > 0, f"CDE: boundary_queries > 0 (got {bdry_q})")
        sp_calls = od.get("search_position_calls", 0)
        check(sp_calls > 0, f"CDE: search_position_calls > 0 (got {sp_calls})")
        _log("INFO", f"cde: sp_calls={sp_calls} bdry_q={bdry_q} "
                     f"pair_q={od.get('collision_severity_pair_queries')} "
                     f"bbox_proxy={bbox_proxy} "
                     f"conf_coll={od.get('collision_severity_backend_confirmed_collisions')}")


def fixture4_backend_name_wired():
    print("\n=== Fixture 4: Backend name wired — collision_severity_backend matches input ===")
    # JSON variant names are snake_case per serde: bbox, jagua_polygon_exact, cde.
    # The output `collision_severity_backend` uses the Rust Debug format (PascalCase).
    cases = [
        (None, "Bbox"),
        ("jagua_polygon_exact", "JaguaPolygonExact"),
    ]
    for backend_arg, expected_substr in cases:
        out = run_solver(base_input(backend=backend_arg))
        od = out.get("optimizer_diagnostics") or {}
        bname = od.get("collision_severity_backend", "")
        check(
            expected_substr in bname,
            f"backend={backend_arg!r}: collision_severity_backend contains "
            f"'{expected_substr}' (got '{bname}')"
        )


def fixture5_all_fields_present():
    print("\n=== Fixture 5: All 9 collision_severity fields present in optimizer_diagnostics ===")
    out = run_solver(base_input(backend="jagua_polygon_exact"))
    od = out.get("optimizer_diagnostics") or {}
    required_fields = [
        "collision_severity_backend",
        "collision_severity_enabled",
        "collision_severity_pair_queries",
        "collision_severity_boundary_queries",
        "collision_severity_probe_queries",
        "collision_severity_backend_confirmed_collisions",
        "collision_severity_backend_confirmed_no_collisions",
        "collision_severity_unsupported_queries",
        "collision_severity_bbox_proxy_uses",
    ]
    for field in required_fields:
        check(field in od, f"field '{field}' present in optimizer_diagnostics")
    if od:
        check(isinstance(od.get("collision_severity_backend"), str),
              f"collision_severity_backend is string "
              f"(got {type(od.get('collision_severity_backend')).__name__})")
        check(isinstance(od.get("collision_severity_enabled"), bool),
              f"collision_severity_enabled is bool "
              f"(got {type(od.get('collision_severity_enabled')).__name__})")
        for field in required_fields[2:]:
            check(isinstance(od.get(field), int),
                  f"{field} is int (got {type(od.get(field)).__name__})")


# ---------------------------------------------------------------------------


def main():
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    print(f"SGH-Q21 collision severity + evaluate_transform smoke script")
    print(f"Binary: {BINARY}")

    fixture1_exact_backend_severity_engine()
    fixture2_bbox_backend_bypasses_severity_engine()
    fixture3_cde_path_no_bbox_proxy()
    fixture4_backend_name_wired()
    fixture5_all_fields_present()

    print()
    print("=" * 60)
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL")
        sys.exit(1)
    else:
        print("SMOKE: PASS")


if __name__ == "__main__":
    main()
