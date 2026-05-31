#!/usr/bin/env python3
"""SGH-Q24R6 native Sparrow tracker/search parity hardening smoke.

This smoke is intentionally strict about architecture and intentionally focused on
tracker/search/worker behavior. It must not be satisfied by re-enabling legacy,
LBF fallback, bbox truth, or compression.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPARROW_DIR = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow"
SPARROW_RS = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow.rs"
ADAPTER = ROOT / "rust" / "vrs_solver" / "src" / "adapter.rs"
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
LV8_FIXTURE = ROOT / "tests" / "fixtures" / "nesting_engine" / "ne2_input_lv8jav.json"
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
    text = re.sub(r"(?s)#\[cfg\(test\)\].*", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    return text


def production_sparrow_sources() -> dict[Path, str]:
    sources: dict[Path, str] = {}
    if SPARROW_DIR.exists():
        for p in sorted(SPARROW_DIR.rglob("*.rs")):
            if "legacy" in p.name.lower():
                continue
            sources[p] = strip_tests_and_comments(read(p))
    elif SPARROW_RS.exists():
        sources[SPARROW_RS] = strip_tests_and_comments(read(SPARROW_RS))
    return sources


def function_body(text: str, fn_name: str) -> str:
    m = re.search(rf"(?:pub\s+)?fn\s+{re.escape(fn_name)}\s*\([^\{{]*\{{", text)
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
    return text[start : i - 1]


def static_architecture_gate() -> None:
    print("\n=== static architecture preservation gate ===")
    sources = production_sparrow_sources()
    check(bool(sources), "production optimizer/sparrow sources exist")
    joined = "\n".join(sources.values())

    for token in [
        "SparrowProblem",
        "SPInstance",
        "SparrowPlacement",
        "SparrowLayout",
        "SparrowSolution",
        "SparrowCollisionTracker",
        "SparrowOptimizer",
        "SparrowSolveResult",
    ]:
        check(token in joined, f"native concept still present: {token}")

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

    projection_allowed = {"solution.rs", "projection.rs", "mod.rs"}
    placement_offenders = []
    for p, t in sources.items():
        if p.name not in projection_allowed and ("crate::io::Placement" in t or "use crate::io::Placement" in t or "use crate::io::{Placement" in t):
            placement_offenders.append(str(p.relative_to(ROOT)))
    check(not placement_offenders, "crate::io::Placement not used as internal native layout type" + (f" ({placement_offenders})" if placement_offenders else ""))

    adapter = strip_tests_and_comments(read(ADAPTER))
    body = function_body(adapter, "run_sparrow_pipeline")
    check(bool(body), "run_sparrow_pipeline found for static scan")
    check("SparrowProblem" in body and "from_solver_input" in body, "run_sparrow_pipeline constructs native SparrowProblem")
    check("SparrowOptimizer" in body and ".solve" in body, "run_sparrow_pipeline calls native SparrowOptimizer::solve")
    for token in ["WorkingLayout::new", "SparrowSeparationKernel", "PhaseOptimizer", "MultiSheetManager", "validate_and_commit_with_backend"]:
        check(token not in body, f"run_sparrow_pipeline does not use {token}")


def static_tracker_search_worker_gate() -> None:
    print("\n=== static tracker/search/worker hardening gate ===")
    sources = production_sparrow_sources()
    joined = "\n".join(sources.values())

    # Q24R5 count-only patterns must be gone from production Sparrow core.
    count_patterns = [
        "pair_loss.insert(key, 1.0)",
        "boundary_loss[i] = 1.0",
        "colliding_layout_idxs.len() as f64",
        "+ if res.boundary_collision { 1.0 } else { 0.0 }",
    ]
    for pat in count_patterns:
        check(pat not in joined, f"no count-only loss pattern: {pat}")

    quant_tokens = [
        "separation_loss",
        "resolution_distance",
        "clearance",
        "probe",
        "binary_refine",
        "bracket",
    ]
    check(any(tok in joined for tok in quant_tokens), "native tracker/search contains quantified separation/probe loss concept")
    check("pair_weight" in joined and "boundary_weight" in joined, "GLS pair and boundary/container weights still present")
    check("total_weighted_loss" in joined and "weighted_loss_for_item" in joined, "weighted loss APIs present")
    check("update_after_move" in joined and "snapshot" in joined and "restore_keep_weights" in joined, "tracker incremental update/snapshot/restore APIs present")

    # Search must not be current-sheet-only. Accept several possible naming styles.
    multi_sheet_tokens = [
        "eligible_sheets",
        "sheet_candidates",
        "for sheet_idx in 0..sheets.len()",
        "sheets.iter().enumerate()",
        "for (sheet_idx, sheet) in sheets",
    ]
    check(any(tok in joined for tok in multi_sheet_tokens), "native search considers multiple eligible sheets/containers")

    search_tokens = ["focused", "global", "coord", "descent", "rotations"]
    for tok in search_tokens:
        check(tok in joined.lower(), f"native search has {tok} concept")

    worker_tokens = ["WorkerCandidate", "worker_count", "run_worker_pass", "best_worker", "compare_worker"]
    check(any(tok in joined for tok in worker_tokens), "real worker candidate/snapshot/competition concepts present")
    check("load" in joined.lower() and "worker" in joined.lower(), "best worker load-back concept present")

    diag_tokens = [
        "worker_candidates_evaluated",
        "global_samples",
        "focused_samples",
        "coord_descent",
        "unsupported_samples",
        "best_eval",
    ]
    # Accept either exact new field names or adapter output references.
    check(sum(1 for tok in diag_tokens if tok in joined) >= 3, "diagnostic fields/updates cover search and worker activity")


def run_solver(inp: dict[str, Any], cap: float = 120.0) -> tuple[dict[str, Any], float]:
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


def base(parts: list[dict[str, Any]], stocks: list[dict[str, Any]], seed: int = 5, tl: int = 20, name: str = "q24r6") -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "project_name": name,
        "seed": seed,
        "time_limit_s": tl,
        "solver_profile": PROFILE,
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "bbox",  # production sparrow_cde must force/use CDE truth anyway
        "rotation_policy": "orthogonal",
        "stocks": stocks,
        "parts": parts,
    }


def common_runtime_checks(out: dict[str, Any], req: int, label: str, ms: float, require_worker: bool) -> None:
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    metrics = out.get("metrics") or {}
    check(out.get("status") == "ok", f"{label}: status ok, got {out.get('status')} ({ms/1000:.1f}s)")
    check(metrics.get("placed_count") == req, f"{label}: placed {req}/{req}, got {metrics.get('placed_count')}")
    check(od.get("pipeline_used") == "sparrow_cde", f"{label}: pipeline_used == sparrow_cde")
    check(od.get("sparrow_converged") is True, f"{label}: sparrow_converged == true")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, f"{label}: final collision pairs == 0")
    check(od.get("sparrow_boundary_violations_final") == 0, f"{label}: final boundary violations == 0")
    check(cbd.get("backend_used") == "cde_adapter", f"{label}: CDE backend used")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, f"{label}: no bbox fallback queries")
    check((od.get("search_position_lbf_fallback_used") or od.get("sparrow_lbf_fallback_used") or 0) == 0, f"{label}: no LBF fallback")
    compression_disabled = od.get("sparrow_compression_disabled") is True
    compression_zero = (od.get("sparrow_compression_passes") or 0) == 0
    check(compression_disabled or compression_zero, f"{label}: compression disabled/gated or zero default passes")
    check(od.get("sparrow_native_model_active") is True, f"{label}: native model active")
    check(od.get("sparrow_native_tracker_active") is True, f"{label}: native tracker active")
    check(od.get("sparrow_old_core_used") is False, f"{label}: old core used false")
    check((od.get("sparrow_search_position_calls") or 0) > 0, f"{label}: search calls > 0")
    check((od.get("sparrow_search_position_samples") or 0) > 0, f"{label}: search samples > 0")
    check((od.get("sparrow_graph_incremental_updates") or od.get("sparrow_native_tracker_incremental_updates") or 0) > 0, f"{label}: native tracker incremental updates > 0")
    if require_worker:
        workers = od.get("sparrow_workers") or od.get("sparrow_worker_count") or 0
        worker_candidates = od.get("sparrow_worker_candidates_evaluated") or 0
        check(workers >= 2, f"{label}: worker count >= 2, got {workers}")
        check(worker_candidates > 0, f"{label}: worker candidates evaluated > 0")


def runtime_medium_gate() -> None:
    print("\n=== runtime medium CDE native tracker/search gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    inp = base(
        parts=[{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        stocks=[{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        seed=5,
        tl=30,
        name="q24r6_medium_native_tracker_search",
    )
    out, ms = run_solver(inp, cap=120.0)
    common_runtime_checks(out, 12, "medium", ms, require_worker=True)


def lv8_types_x1_input() -> tuple[dict[str, Any] | None, int]:
    if not LV8_FIXTURE.exists():
        return None, 0
    data = json.loads(LV8_FIXTURE.read_text(encoding="utf-8"))
    sheet = data.get("sheet") or {}
    parts: list[dict[str, Any]] = []
    for p in data.get("parts", []):
        pts = p.get("outer_points_mm") or []
        if not pts:
            continue
        xs = [float(a[0]) for a in pts]
        ys = [float(a[1]) for a in pts]
        parts.append(
            {
                "id": p["id"],
                "quantity": 1,
                "width": max(xs) - min(xs),
                "height": max(ys) - min(ys),
                "allowed_rotations_deg": p.get("allowed_rotations_deg", [0, 90, 180, 270]),
                "outer_points": pts,
            }
        )
    inp = base(
        parts=parts,
        stocks=[
            {
                "id": "LV8_SHEET",
                "quantity": 2,
                "width": float(sheet.get("width_mm", 1500.0)),
                "height": float(sheet.get("height_mm", 3000.0)),
            }
        ],
        seed=11,
        tl=45,
        name="q24r6_lv8_12types_x1_native_smoke",
    )
    inp["collision_backend"] = "cde"
    return inp, len(parts)


def runtime_lv8_12types_gate() -> None:
    print("\n=== runtime LV8 12 part types x1 native smoke ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    inp, req = lv8_types_x1_input()
    check(inp is not None, f"LV8 fixture exists at {LV8_FIXTURE}")
    if inp is None:
        return
    check(req == 12, f"LV8 fixture converted to 12 part types, got {req}")
    out, ms = run_solver(inp, cap=180.0)
    common_runtime_checks(out, req, "lv8_12types_x1", ms, require_worker=False)


def main() -> None:
    print("SGH-Q24R6 native Sparrow tracker/search parity hardening smoke")
    static_architecture_gate()
    static_tracker_search_worker_gate()
    runtime_medium_gate()
    runtime_lv8_12types_gate()
    print("\n" + "=" * 72)
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL:
        print("SMOKE: FAIL")
        sys.exit(1)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
