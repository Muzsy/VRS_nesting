#!/usr/bin/env python3
"""SGH-Q24R7 native Sparrow sampler/evaluator + LV8 first-sheet smoke.

This smoke guards the Q24R5/Q24R6 native architecture, checks that Q24R7 did
real sampler/evaluator work instead of returning to AABB ordering, and builds the
LV8 dense probe from the Nest&Cut reference layout 1 / sheet 1 composition.

The first-sheet dense probe is intentionally allowed to report PARTIAL without
failing the whole smoke, because this is a stress probe and the current fixture
uses solver-ready orthogonal rotations while the external report used all
rotations + 5 mm gaps. It must still be generated and run honestly with native
CDE, no bbox truth, no LBF/legacy fallback, and no compression.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPARROW_DIR = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow"
SPARROW_RS = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow.rs"
ADAPTER = ROOT / "rust" / "vrs_solver" / "src" / "adapter.rs"
BINARY = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
LV8_FIXTURE = ROOT / "tests" / "fixtures" / "nesting_engine" / "ne2_input_lv8jav.json"
PROFILE = "jagua_optimizer_phase1_outer_only"

FIRST_SHEET_QTY: dict[str, int] = {
    "LV8_01170_10db": 10,
    "LV8_02048_20db": 7,
    "LV8_02049_50db": 50,
    "Lv8_07919_16db": 13,
    "Lv8_07920_50db": 12,
    "Lv8_07921_50db": 33,
    "Lv8_15435_10db": 10,
    "Lv8_11612_6db": 3,
    "Lv8_15348_6db": 4,
    "Lv8_10059_10db": 10,
    "LV8_00035_28db": 28,
    "LV8_00057_20db": 11,
}

PASS = 0
FAIL = 0
PARTIAL = 0


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def note_partial(cond: bool, msg: str) -> None:
    global PASS, PARTIAL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        PARTIAL += 1
        print(f"  [PARTIAL] {msg}")


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
    ]
    for token in forbidden:
        offenders = [str(p.relative_to(ROOT)) for p, t in sources.items() if token in t]
        check(not offenders, f"no {token} in production optimizer/sparrow sources" + (f" ({offenders})" if offenders else ""))

    adapter = strip_tests_and_comments(read(ADAPTER))
    body = function_body(adapter, "run_sparrow_pipeline")
    check(bool(body), "run_sparrow_pipeline found for static scan")
    check("SparrowProblem" in body and "from_solver_input" in body, "run_sparrow_pipeline constructs native SparrowProblem")
    check("SparrowOptimizer" in body and ".solve" in body, "run_sparrow_pipeline calls native SparrowOptimizer::solve")
    for token in ["WorkingLayout::new", "SparrowSeparationKernel", "PhaseOptimizer", "MultiSheetManager", "validate_and_commit_with_backend"]:
        check(token not in body, f"run_sparrow_pipeline does not use {token}")


def static_sampler_evaluator_gate() -> None:
    print("\n=== static sampler/evaluator gate ===")
    sources = production_sparrow_sources()
    joined = "\n".join(sources.values())
    lower = joined.lower()

    # Q24R6 accepted this as a temporary ordering proxy. Q24R7 must replace it.
    check("aabb_penetration" not in joined, "aabb_penetration not used in production Sparrow sample ordering/evaluator")
    check("boundary_spill" not in joined or "broad" in lower, "boundary spill is not the main infeasible evaluator unless explicitly broad-phase")

    evaluator_tokens = [
        "SampleEvaluator",
        "SepEvaluator",
        "CandidateEvaluator",
        "evaluate_candidate",
        "score_candidate",
        "polygon_overlap",
        "quantified_candidate",
        "candidate_loss",
    ]
    check(any(tok in joined for tok in evaluator_tokens), "native sample/evaluator concept exists")
    check("CdeCandidateSession" in joined or "CdeAdapter" in joined, "candidate evaluation remains CDE-backed")
    check("coord" in lower and "descent" in lower, "coordinate descent/refinement still present")
    check("focused" in lower and "global" in lower, "focused + global sampling concepts present")

    # Multi-container must be part of candidate pool, not current-sheet-only fallback.
    pool_tokens = [
        "all_eligible_sheets",
        "eligible_sheets",
        "container_candidates",
        "sheet_candidates",
        "candidate_pool",
        "for sheet_idx in 0..sheets.len()",
        "sheets.iter().enumerate()",
    ]
    check(any(tok in joined for tok in pool_tokens), "candidate pool spans eligible sheets/containers")
    fallback_only_smells = [
        "if best_clear.is_some() { break",
        "if found_clear_on_current_sheet",
        "current sheet has no clear",
    ]
    check(not any(smell in lower for smell in fallback_only_smells), "multi-container search is not obvious fallback-only current-sheet logic")

    worker_tokens = ["WorkerCandidate", "worker_count", "run_worker_pass", "best_worker", "compare_worker", "load_best_worker"]
    check(sum(1 for tok in worker_tokens if tok in joined) >= 4, "worker snapshot/competition/load-back concepts remain present")


def run_solver(inp: dict[str, Any], cap: float) -> tuple[dict[str, Any], float]:
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
            return {"status": "error", "returncode": proc.returncode, "stderr": proc.stderr[-2000:], "stdout": proc.stdout[-2000:]}, ms
        return json.loads(op.read_text(encoding="utf-8")), ms


def base(parts: list[dict[str, Any]], stocks: list[dict[str, Any]], seed: int, tl: int, name: str) -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "project_name": name,
        "seed": seed,
        "time_limit_s": tl,
        "solver_profile": PROFILE,
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "rotation_policy": "orthogonal",
        "stocks": stocks,
        "parts": parts,
    }


def runtime_native_checks(out: dict[str, Any], label: str, require_ok: bool = True) -> tuple[int, dict[str, Any], dict[str, Any]]:
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    metrics = out.get("metrics") or {}
    placed = int(metrics.get("placed_count") or 0)
    if require_ok:
        check(out.get("status") == "ok", f"{label}: status ok, got {out.get('status')}")
    else:
        check(out.get("status") in {"ok", "partial"}, f"{label}: status ok or partial, got {out.get('status')}")
    check(od.get("pipeline_used") == "sparrow_cde", f"{label}: pipeline_used == sparrow_cde")
    check((cbd.get("backend_used") == "cde_adapter") or (out.get("status") == "partial"), f"{label}: CDE backend used when completed")
    check((cbd.get("bbox_fallback_queries") or 0) == 0, f"{label}: no bbox fallback queries")
    check((od.get("search_position_lbf_fallback_used") or od.get("sparrow_lbf_fallback_used") or 0) == 0, f"{label}: no LBF fallback")
    compression_disabled = od.get("sparrow_compression_disabled") is True
    compression_zero = (od.get("sparrow_compression_passes") or 0) == 0
    check(compression_disabled or compression_zero, f"{label}: compression disabled/gated or zero default passes")
    check(od.get("sparrow_native_model_active") is True, f"{label}: native model active")
    check(od.get("sparrow_native_tracker_active") is True, f"{label}: native tracker active")
    check(od.get("sparrow_old_core_used") is False, f"{label}: old core used false")
    return placed, od, cbd


def runtime_medium_gate() -> None:
    print("\n=== runtime medium CDE gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    inp = base(
        parts=[{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        stocks=[{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        seed=5,
        tl=30,
        name="q24r7_medium_native_sampler_evaluator",
    )
    out, ms = run_solver(inp, cap=120.0)
    placed, od, _ = runtime_native_checks(out, "medium", require_ok=True)
    check(placed == 12, f"medium: placed 12/12, got {placed} ({ms/1000:.1f}s)")
    check(od.get("sparrow_converged") is True, "medium: sparrow_converged true")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, "medium: final collision pairs 0")
    check(od.get("sparrow_boundary_violations_final") == 0, "medium: final boundary violations 0")


def part_from_fixture(p: dict[str, Any], quantity: int) -> dict[str, Any]:
    pts = p.get("outer_points_mm") or []
    xs = [float(a[0]) for a in pts]
    ys = [float(a[1]) for a in pts]
    return {
        "id": p["id"],
        "quantity": quantity,
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
        "allowed_rotations_deg": p.get("allowed_rotations_deg", [0, 90, 180, 270]),
        "outer_points": pts,
    }


def lv8_input(quantity_by_id: dict[str, int], stocks_qty: int, seed: int, tl: int, name: str) -> tuple[dict[str, Any] | None, int]:
    if not LV8_FIXTURE.exists():
        return None, 0
    data = json.loads(LV8_FIXTURE.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in data.get("parts", [])}
    missing = sorted(set(quantity_by_id) - set(by_id))
    if missing:
        raise AssertionError(f"missing LV8 fixture ids: {missing}")
    sheet = data.get("sheet") or {}
    parts = [part_from_fixture(by_id[pid], qty) for pid, qty in quantity_by_id.items() if qty > 0]
    inp = base(
        parts=parts,
        stocks=[
            {
                "id": "LV8_SHEET",
                "quantity": stocks_qty,
                "width": float(sheet.get("width_mm", 1500.0)),
                "height": float(sheet.get("height_mm", 3000.0)),
            }
        ],
        seed=seed,
        tl=tl,
        name=name,
    )
    return inp, sum(quantity_by_id.values())


def runtime_lv8_12types_gate() -> None:
    print("\n=== runtime LV8 12 types x1 regression ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    fixture = json.loads(LV8_FIXTURE.read_text(encoding="utf-8"))
    qty = {p["id"]: 1 for p in fixture.get("parts", [])}
    inp, req = lv8_input(qty, stocks_qty=2, seed=11, tl=45, name="q24r7_lv8_12types_x1_regression")
    check(inp is not None, f"LV8 fixture exists at {LV8_FIXTURE}")
    check(req == 12, f"LV8 x1 required count 12, got {req}")
    out, ms = run_solver(inp, cap=180.0)
    placed, od, _ = runtime_native_checks(out, "lv8_12types_x1", require_ok=True)
    check(placed == req, f"lv8_12types_x1: placed {req}/{req}, got {placed} ({ms/1000:.1f}s)")
    check(od.get("sparrow_collision_graph_final_pairs") == 0, "lv8_12types_x1: final collision pairs 0")
    check(od.get("sparrow_boundary_violations_final") == 0, "lv8_12types_x1: final boundary violations 0")


def runtime_lv8_reference_sheet1_gate() -> None:
    print("\n=== runtime LV8 reference sheet 1 dense probe ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    req = sum(FIRST_SHEET_QTY.values())
    check(req == 191, f"first-sheet quantity vector totals 191, got {req}")
    inp, req2 = lv8_input(FIRST_SHEET_QTY, stocks_qty=1, seed=17, tl=180, name="q24r7_lv8_reference_sheet1_191")
    check(inp is not None, f"LV8 fixture exists at {LV8_FIXTURE}")
    check(req2 == 191, f"generated first-sheet input requires 191, got {req2}")
    out, ms = run_solver(inp, cap=360.0)
    placed, od, _ = runtime_native_checks(out, "lv8_reference_sheet1", require_ok=False)
    print(f"  [INFO] lv8_reference_sheet1 status={out.get('status')} placed={placed}/191 runtime={ms/1000:.1f}s")
    if out.get("status") == "ok" and placed == 191:
        check(od.get("sparrow_collision_graph_final_pairs") == 0, "lv8_reference_sheet1: final collision pairs 0")
        check(od.get("sparrow_boundary_violations_final") == 0, "lv8_reference_sheet1: final boundary violations 0")
        note_partial(True, "lv8_reference_sheet1: FULL 191/191 achieved")
    else:
        # This is a mandatory dense probe, not yet necessarily a hard full-fit gate.
        note_partial(False, f"lv8_reference_sheet1: partial/full-fit not achieved yet; placed {placed}/191. Report exact blockers.")


def main() -> None:
    print("SGH-Q24R7 native Sparrow sampler/evaluator + LV8 first-sheet smoke")
    static_architecture_gate()
    static_sampler_evaluator_gate()
    runtime_medium_gate()
    runtime_lv8_12types_gate()
    runtime_lv8_reference_sheet1_gate()
    print("\n" + "=" * 72)
    print(f"Results: {PASS} passed, {FAIL} failed, {PARTIAL} partial notes")
    if FAIL:
        print("SMOKE: FAIL")
        sys.exit(1)
    if PARTIAL:
        print("SMOKE: PASS_WITH_PARTIAL_DENSE_PROBE")
        sys.exit(0)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
