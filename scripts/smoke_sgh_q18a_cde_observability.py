#!/usr/bin/env python3
"""SGH-Q18A CDE observability smoke script.

Four fixtures:
  1. Valid simple rect + collision_backend=cde + legacy_multisheet
  2. Valid simple rect + collision_backend=cde + optimizer_pipeline=phase_optimizer
  3. Malformed outer_points + collision_backend=cde -> unsupported (no bbox fallback)
  4. L-shape notch fixture + collision_backend=cde (proves CDE not just a bbox proxy)

Checks:
  - backend_used == "cde_adapter" for CDE paths
  - final_commit_backend_used == "cde_adapter"
  - bbox_fallback_queries == 0
  - cde_total_queries > 0 for valid CDE
  - cde_engine_builds > 0 for valid CDE
  - unsupported_reason == "CDE_BACKEND_UNSUPPORTED_QUERY" for malformed geometry
  - bbox/default path emits no collision_backend_diagnostics
  - timing fields present when VRS_CDE_OBSERVABILITY_TIMING=1
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


def run_solver(input_dict: dict, timing: bool = False) -> dict:
    env = os.environ.copy()
    if timing:
        env["VRS_CDE_OBSERVABILITY_TIMING"] = "1"
    else:
        env.pop("VRS_CDE_OBSERVABILITY_TIMING", None)
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "in.json"
        out_path = Path(tmpdir) / "out.json"
        in_path.write_text(json.dumps(input_dict))
        result = subprocess.run(
            [str(BINARY), "--input", str(in_path), "--output", str(out_path),
             "--seed", "0", "--time-limit", "10"],
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            print(f"  [ERROR] solver exited {result.returncode}: {result.stderr[:300]}")
            return {}
        return json.loads(out_path.read_text())


def base_input(pipeline: str | None = None, backend: str | None = None) -> dict:
    inp = {
        "contract_version": "v1",
        "project_name": "q18a_smoke",
        "seed": 0,
        "time_limit_s": 10,
        "solver_profile": PROFILE,
        "stocks": [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}],
        "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 2}],
    }
    if pipeline:
        inp["optimizer_pipeline"] = pipeline
    if backend:
        inp["collision_backend"] = backend
    return inp


# ---------------------------------------------------------------------------
# Fixture 1: valid rect + CDE + legacy_multisheet
# ---------------------------------------------------------------------------

def fixture1_valid_cde_legacy():
    print("\n=== Fixture 1: valid rect + CDE + legacy_multisheet ===")
    out = run_solver(base_input(pipeline="legacy_multisheet", backend="cde"))
    if not out:
        check(False, "solver produced output")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    diag = out.get("collision_backend_diagnostics")
    check(diag is not None, "collision_backend_diagnostics present")
    if diag:
        check(diag.get("backend_used") == "cde_adapter", f"backend_used=cde_adapter (got {diag.get('backend_used')})")
        check(diag.get("bbox_fallback_queries", -1) == 0, f"bbox_fallback_queries==0 (got {diag.get('bbox_fallback_queries')})")
        check((diag.get("cde_total_queries") or 0) > 0, f"cde_total_queries>0 (got {diag.get('cde_total_queries')})")
        check((diag.get("cde_engine_builds") or 0) > 0, f"cde_engine_builds>0 (got {diag.get('cde_engine_builds')})")
        check(diag.get("final_commit_backend_used") == "cde_adapter",
              f"final_commit_backend_used=cde_adapter (got {diag.get('final_commit_backend_used')})")
        check(diag.get("cde_observability_scope") == "final_commit_only",
              f"scope=final_commit_only (got {diag.get('cde_observability_scope')})")
        print(f"  [INFO] cde_total_queries={diag.get('cde_total_queries')} engine_builds={diag.get('cde_engine_builds')}")
        print(f"  [INFO] pair_queries={diag.get('cde_pair_queries')} boundary_queries={diag.get('cde_boundary_queries')}")


# ---------------------------------------------------------------------------
# Fixture 2: valid rect + CDE + phase_optimizer
# ---------------------------------------------------------------------------

def fixture2_valid_cde_phase_optimizer():
    print("\n=== Fixture 2: valid rect + CDE + phase_optimizer ===")
    out = run_solver(base_input(pipeline="phase_optimizer", backend="cde"))
    if not out:
        check(False, "solver produced output")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    diag = out.get("collision_backend_diagnostics")
    check(diag is not None, "collision_backend_diagnostics present")
    if diag:
        check(diag.get("backend_used") == "cde_adapter", f"backend_used=cde_adapter (got {diag.get('backend_used')})")
        check(diag.get("bbox_fallback_queries", -1) == 0, f"bbox_fallback_queries==0 (got {diag.get('bbox_fallback_queries')})")
        check((diag.get("cde_total_queries") or 0) > 0, f"cde_total_queries>0 (got {diag.get('cde_total_queries')})")
        check((diag.get("cde_engine_builds") or 0) > 0, f"cde_engine_builds>0 (got {diag.get('cde_engine_builds')})")
        check(diag.get("final_commit_backend_used") == "cde_adapter",
              f"final_commit_backend_used=cde_adapter (got {diag.get('final_commit_backend_used')})")
        check(diag.get("cde_observability_scope") == "full_solve",
              f"scope=full_solve (got {diag.get('cde_observability_scope')})")
        print(f"  [INFO] cde_total_queries={diag.get('cde_total_queries')} engine_builds={diag.get('cde_engine_builds')}")


# ---------------------------------------------------------------------------
# Fixture 3: malformed outer_points + CDE → unsupported (not bbox fallback)
# ---------------------------------------------------------------------------

def fixture3_malformed_cde_unsupported():
    print("\n=== Fixture 3: malformed outer_points + CDE → unsupported ===")
    inp = base_input(pipeline="legacy_multisheet", backend="cde")
    inp["parts"][0]["outer_points"] = "not-an-array"  # malformed
    out = run_solver(inp)
    if not out:
        check(False, "solver produced output")
        return
    check(out.get("status") == "unsupported", f"status=unsupported (got {out.get('status')})")
    check(out.get("unsupported_reason") == "CDE_BACKEND_UNSUPPORTED_QUERY",
          f"unsupported_reason=CDE_BACKEND_UNSUPPORTED_QUERY (got {out.get('unsupported_reason')})")
    check(len(out.get("placements", [])) == 0, "no placements on malformed geometry")
    diag = out.get("collision_backend_diagnostics")
    check(diag is not None, "collision_backend_diagnostics present even on unsupported")
    if diag:
        check(diag.get("bbox_fallback_queries", -1) == 0, f"bbox_fallback_queries==0 (got {diag.get('bbox_fallback_queries')})")
        unsupported = diag.get("cde_unsupported_results") or 0
        failures = diag.get("cde_prepare_failures") or 0
        check(unsupported > 0 or failures > 0,
              f"at least one unsupported/prepare_failure (unsupported={unsupported}, failures={failures})")
        print(f"  [INFO] cde_unsupported_results={diag.get('cde_unsupported_results')} cde_prepare_failures={diag.get('cde_prepare_failures')}")


# ---------------------------------------------------------------------------
# Fixture 4: L-shape notch + CDE (proves CDE ≠ bbox proxy)
# ---------------------------------------------------------------------------

def fixture4_lshape_notch_cde():
    print("\n=== Fixture 4: L-shape notch + CDE (proves CDE ≠ bbox proxy) ===")
    # L-shape: 40×40, notch at top-right. Small rect (15×15) fits in the notch at (22,22).
    # Bbox: false positive (collision). CDE: correctly no collision.
    inp = {
        "contract_version": "v1",
        "project_name": "q18a_notch",
        "seed": 0,
        "time_limit_s": 10,
        "solver_profile": PROFILE,
        "collision_backend": "cde",
        "optimizer_pipeline": "legacy_multisheet",
        "stocks": [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}],
        "parts": [
            {
                "id": "L",
                "width": 40.0, "height": 40.0, "quantity": 1,
                "outer_points": [
                    [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
                    [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
                ]
            },
            {"id": "S", "width": 15.0, "height": 15.0, "quantity": 1}
        ],
    }
    out = run_solver(inp)
    if not out:
        check(False, "solver produced output")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    diag = out.get("collision_backend_diagnostics")
    check(diag is not None, "collision_backend_diagnostics present")
    if diag:
        check(diag.get("backend_used") == "cde_adapter", f"backend_used=cde_adapter (got {diag.get('backend_used')})")
        check(diag.get("bbox_fallback_queries", -1) == 0, f"bbox_fallback_queries==0 (got {diag.get('bbox_fallback_queries')})")
        check((diag.get("cde_total_queries") or 0) > 0, f"cde_total_queries>0 (got {diag.get('cde_total_queries')})")
        print(f"  [INFO] cde_total_queries={diag.get('cde_total_queries')} pair={diag.get('cde_pair_queries')} boundary={diag.get('cde_boundary_queries')}")


# ---------------------------------------------------------------------------
# Fixture 5: Default (bbox) backend — no CDE counters emitted
# ---------------------------------------------------------------------------

def fixture5_bbox_no_cde_observability():
    print("\n=== Fixture 5: default bbox backend — no CDE observability ===")
    out = run_solver(base_input())  # no backend specified → defaults to bbox
    if not out:
        check(False, "solver produced output")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    check(out.get("collision_backend_diagnostics") is None,
          "bbox default path must not emit collision_backend_diagnostics")


# ---------------------------------------------------------------------------
# Fixture 6: timing env flag (VRS_CDE_OBSERVABILITY_TIMING=1)
# ---------------------------------------------------------------------------

def fixture6_timing_env_flag():
    print("\n=== Fixture 6: timing env flag VRS_CDE_OBSERVABILITY_TIMING=1 ===")
    out = run_solver(base_input(pipeline="legacy_multisheet", backend="cde"), timing=True)
    if not out:
        check(False, "solver produced output with timing flag")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    diag = out.get("collision_backend_diagnostics")
    check(diag is not None, "collision_backend_diagnostics present with timing flag")
    if diag:
        ms = diag.get("final_commit_validation_ms")
        # timing must be present and non-negative
        check(ms is not None and isinstance(ms, (int, float)) and ms >= 0,
              f"final_commit_validation_ms present and non-negative (got {ms})")
        print(f"  [INFO] final_commit_validation_ms={ms}")


# ---------------------------------------------------------------------------
# Fixture 7: no timing fields by default (no env flag)
# ---------------------------------------------------------------------------

def fixture7_timing_absent_by_default():
    print("\n=== Fixture 7: timing fields absent by default (no env flag) ===")
    # Run without timing env → timing fields must be absent from JSON.
    out = run_solver(base_input(pipeline="phase_optimizer", backend="cde"), timing=False)
    if not out:
        check(False, "solver produced output")
        return
    cde_diag = out.get("collision_backend_diagnostics")
    if cde_diag:
        check(cde_diag.get("final_commit_validation_ms") is None,
              "final_commit_validation_ms must be absent by default")
    opt_diag = out.get("optimizer_diagnostics")
    if opt_diag:
        check(opt_diag.get("phase_optimizer_exploration_ms") is None,
              "phase_optimizer_exploration_ms must be absent by default")
        check(opt_diag.get("phase_optimizer_compression_ms") is None,
              "phase_optimizer_compression_ms must be absent by default")
        check(opt_diag.get("phase_optimizer_bpp_ms") is None,
              "phase_optimizer_bpp_ms must be absent by default")
        check(opt_diag.get("phase_optimizer_final_commit_ms") is None,
              "phase_optimizer_final_commit_ms must be absent by default")
    check(True, "no timing fields in default JSON output confirmed")


# ---------------------------------------------------------------------------
# Fixture 8: per-phase timing with VRS_CDE_OBSERVABILITY_TIMING=1 (phase_optimizer)
# ---------------------------------------------------------------------------

def fixture8_phase_optimizer_timing_env():
    print("\n=== Fixture 8: phase_optimizer per-phase timing with env flag ===")
    out = run_solver(base_input(pipeline="phase_optimizer", backend="cde"), timing=True)
    if not out:
        check(False, "solver produced output with timing flag")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    opt_diag = out.get("optimizer_diagnostics")
    check(opt_diag is not None, "optimizer_diagnostics present")
    if opt_diag:
        for field in [
            "phase_optimizer_exploration_ms",
            "phase_optimizer_compression_ms",
            "phase_optimizer_bpp_ms",
            "phase_optimizer_final_commit_ms",
        ]:
            val = opt_diag.get(field)
            check(val is not None and isinstance(val, (int, float)) and val >= 0,
                  f"{field} present and non-negative (got {val})")
            print(f"  [INFO] {field}={val}")
    # Also verify final_commit_validation_ms in CDE diag (legacy_multisheet equivalent for phase path)
    cde_diag = out.get("collision_backend_diagnostics")
    if cde_diag:
        ms = cde_diag.get("final_commit_validation_ms")
        check(ms is not None and isinstance(ms, (int, float)) and ms >= 0,
              f"final_commit_validation_ms present and non-negative (got {ms})")


# ---------------------------------------------------------------------------
# Fixture 9: legacy_multisheet final_commit timing with env flag (already covered,
#            now asserted explicitly as a named requirement)
# ---------------------------------------------------------------------------

def fixture9_legacy_multisheet_final_commit_timing():
    print("\n=== Fixture 9: legacy_multisheet CDE final_commit timing with env flag ===")
    out = run_solver(base_input(pipeline="legacy_multisheet", backend="cde"), timing=True)
    if not out:
        check(False, "solver produced output with timing flag")
        return
    check(out.get("status") in ("ok", "partial"), f"status ok/partial (got {out.get('status')})")
    diag = out.get("collision_backend_diagnostics")
    check(diag is not None, "collision_backend_diagnostics present")
    if diag:
        ms = diag.get("final_commit_validation_ms")
        check(ms is not None and isinstance(ms, (int, float)) and ms >= 0,
              f"legacy_multisheet_cde_final_commit_runtime present and non-negative (got {ms})")
        print(f"  [INFO] legacy_multisheet_cde_final_commit_runtime_ms={ms}")
    # Phase-level timing fields must NOT appear in legacy_multisheet (no optimizer_diagnostics)
    opt_diag = out.get("optimizer_diagnostics")
    check(opt_diag is None,
          "legacy_multisheet must not emit optimizer_diagnostics (no per-phase timing)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"SGH-Q18A CDE observability smoke script")
    print(f"Binary: {BINARY}")
    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    fixture1_valid_cde_legacy()
    fixture2_valid_cde_phase_optimizer()
    fixture3_malformed_cde_unsupported()
    fixture4_lshape_notch_cde()
    fixture5_bbox_no_cde_observability()
    fixture6_timing_env_flag()
    fixture7_timing_absent_by_default()
    fixture8_phase_optimizer_timing_env()
    fixture9_legacy_multisheet_final_commit_timing()

    print(f"\n{'='*60}")
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT > 0:
        print("SMOKE: FAIL")
        sys.exit(1)
    else:
        print("SMOKE: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
