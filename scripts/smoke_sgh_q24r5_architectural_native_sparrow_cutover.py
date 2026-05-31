#!/usr/bin/env python3
"""SGH-Q24R5 architectural native Sparrow cutover smoke.

This smoke is intentionally strict. It is designed to prevent another hybrid
"Sparrow-shaped VRS core" from passing as a native cutover.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPARROW_DIR = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow"
SPARROW_RS = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow.rs"
ADAPTER = ROOT / "rust" / "vrs_solver" / "src" / "adapter.rs"
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"

PASS = 0
FAIL = 0


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def strip_tests_and_comments(text: str) -> str:
    # Remove most comments and cfg(test) modules. This is a static smoke, not a parser.
    text = re.sub(r"(?s)#\[cfg\(test\)\].*", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    return text


def production_sparrow_sources() -> dict[Path, str]:
    sources: dict[Path, str] = {}
    if SPARROW_DIR.exists():
        for p in sorted(SPARROW_DIR.rglob("*.rs")):
            # Do not count quarantined legacy files as production only if their filename says legacy.
            if "legacy" in p.name.lower():
                continue
            sources[p] = strip_tests_and_comments(read(p))
    elif SPARROW_RS.exists():
        sources[SPARROW_RS] = strip_tests_and_comments(read(SPARROW_RS))
    return sources


def function_body(text: str, fn_name: str) -> str:
    m = re.search(rf"fn\s+{re.escape(fn_name)}\s*\([^\{{]*\{{", text)
    if not m:
        return ""
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start:i - 1]


def static_native_model_gate() -> None:
    print("\n=== static native Sparrow architecture gate ===")
    sources = production_sparrow_sources()
    check(bool(sources), "production optimizer/sparrow sources exist")

    joined = "\n".join(sources.values())
    required = [
        "SparrowProblem",
        "SPInstance",
        "SparrowPlacement",
        "SparrowLayout",
        "SparrowSolution",
        "SparrowCollisionTracker",
        "SparrowOptimizer",
        "SparrowSolveResult",
    ]
    for token in required:
        check(token in joined, f"native concept present: {token}")

    forbidden = [
        "WorkingLayout",
        "VrsCollisionTracker",
        "SparrowSeparationKernel",
        "search_position_for_target",
        "build_constructive_seed_layout",
        "PhaseOptimizer",
        "MultiSheetManager",
        "build_initial_layout_with_rotation_context",
    ]
    for token in forbidden:
        offenders = [str(p.relative_to(ROOT)) for p, t in sources.items() if token in t]
        check(not offenders, f"no {token} in production optimizer/sparrow sources" + (f" ({offenders})" if offenders else ""))

    # crate::io::Placement is allowed only in projection/output files, never layout/tracker/search/state.
    projection_allowed = {"solution.rs", "projection.rs", "mod.rs"}
    placement_offenders = []
    for p, t in sources.items():
        if p.name not in projection_allowed and ("crate::io::Placement" in t or "use crate::io::Placement" in t or "use crate::io::{Placement" in t):
            placement_offenders.append(str(p.relative_to(ROOT)))
    check(not placement_offenders, "crate::io::Placement not used as internal native layout type" + (f" ({placement_offenders})" if placement_offenders else ""))

    adapter = strip_tests_and_comments(read(ADAPTER))
    body = function_body(adapter, "run_sparrow_pipeline")
    check(bool(body), "run_sparrow_pipeline found for static scan")
    for token in [
        "WorkingLayout::new",
        "SparrowSeparationKernel",
        "build_constructive_seed_layout",
        "PhaseOptimizer",
        "MultiSheetManager",
        "build_initial_layout_with_rotation_context",
    ]:
        check(token not in body, f"run_sparrow_pipeline does not use {token}")
    check("SparrowProblem" in body or "from_solver_input" in body, "run_sparrow_pipeline constructs native SparrowProblem")
    check("SparrowOptimizer" in body and ".solve" in body, "run_sparrow_pipeline calls native SparrowOptimizer::solve")


def run_solver(inp: dict, cap: float = 90.0) -> tuple[dict, float]:
    with tempfile.TemporaryDirectory() as tmp:
        ip = Path(tmp) / "input.json"
        op = Path(tmp) / "output.json"
        ip.write_text(json.dumps(inp), encoding="utf-8")
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(BINARY), "--input", str(ip), "--output", str(op)],
                capture_output=True,
                text=True,
                timeout=cap,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}, (time.perf_counter() - t0) * 1000.0
        ms = (time.perf_counter() - t0) * 1000.0
        if proc.returncode != 0:
            return {
                "status": "error",
                "returncode": proc.returncode,
                "stderr": proc.stderr[-2000:],
                "stdout": proc.stdout[-2000:],
            }, ms
        return json.loads(op.read_text(encoding="utf-8")), ms


def base(parts, stocks, seed=5, tl=20):
    return {
        "contract_version": "v1",
        "project_name": "q24r5_architectural_native_sparrow_cutover",
        "seed": seed,
        "time_limit_s": tl,
        "solver_profile": PROFILE,
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "bbox",  # production sparrow_cde must force CDE anyway
        "rotation_policy": "orthogonal",
        "stocks": stocks,
        "parts": parts,
    }


def runtime_medium_cde_gate() -> None:
    print("\n=== runtime medium CDE native cutover gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    inp = base(
        parts=[{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        stocks=[{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        seed=5,
        tl=20,
    )
    out, ms = run_solver(inp, cap=90.0)
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    metrics = out.get("metrics") or {}

    check(out.get("status") == "ok", f"status ok, got {out.get('status')} ({ms/1000:.1f}s)")
    check(metrics.get("placed_count") == 12, f"placed 12/12, got {metrics.get('placed_count')}")
    check(od.get("pipeline_used") == "sparrow_cde", "pipeline_used == sparrow_cde")
    check(od.get("sparrow_converged") is True, "sparrow_converged == true")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, "final collision pairs == 0")
    check(od.get("sparrow_boundary_violations_final") == 0, "final boundary violations == 0")
    check(cbd.get("backend_used") == "cde_adapter", "CDE backend used even when bbox requested")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, "no bbox fallback queries")
    check((od.get("sparrow_lbf_fallback_used") or 0) == 0, "no LBF fallback")
    compression_disabled = od.get("sparrow_compression_disabled") is True
    compression_zero = (od.get("sparrow_compression_passes") or 0) == 0
    check(compression_disabled or compression_zero, "compression disabled/gated or zero default passes")

    # Q24R5 must add at least one explicit runtime proof field.
    native_active = od.get("sparrow_native_model_active") is True or od.get("native_sparrow_model_active") is True
    native_tracker = od.get("sparrow_native_tracker_active") is True or od.get("native_sparrow_tracker_active") is True
    old_core_false = od.get("sparrow_old_core_used") is False or od.get("old_core_used") is False
    check(native_active, "native model diagnostic active == true")
    check(native_tracker, "native tracker diagnostic active == true")
    check(old_core_false, "old core diagnostic used == false")


def main() -> None:
    print("SGH-Q24R5 architectural native Sparrow cutover smoke")
    static_native_model_gate()
    runtime_medium_cde_gate()
    print("\n" + "=" * 72)
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("SMOKE: FAIL")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
