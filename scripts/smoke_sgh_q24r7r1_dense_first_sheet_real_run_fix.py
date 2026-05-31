#!/usr/bin/env python3
"""SGH-Q24R7-R1 dense first-sheet real-run smoke.

This smoke is intentionally stricter than Q24R7: the 191-instance LV8
first-sheet probe may be PARTIAL, but it must be a real bounded native Sparrow
CDE search. Early guarded partial returns are failures.
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


def partial(cond: bool, msg: str) -> None:
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
    print("\n=== static architecture gate ===")
    sources = production_sparrow_sources()
    joined = "\n".join(sources.values())
    check(bool(sources), "production optimizer/sparrow sources exist")
    for token in [
        "SparrowProblem", "SPInstance", "SparrowPlacement", "SparrowLayout",
        "SparrowSolution", "SparrowCollisionTracker", "SparrowOptimizer", "SparrowSolveResult",
    ]:
        check(token in joined, f"native concept present: {token}")
    forbidden = [
        "WorkingLayout", "VrsCollisionTracker", "SparrowSeparationKernel",
        "search_position_for_target", "build_constructive_seed_layout",
        "PhaseOptimizer", "MultiSheetManager",
    ]
    for token in forbidden:
        offenders = [str(p.relative_to(ROOT)) for p, txt in sources.items() if token in txt]
        check(not offenders, f"no {token} in production optimizer/sparrow" + (f" ({offenders})" if offenders else ""))
    adapter = strip_tests_and_comments(read(ADAPTER))
    body = function_body(adapter, "run_sparrow_pipeline")
    check("SparrowProblem" in body and "from_solver_input" in body, "adapter constructs native SparrowProblem")
    check("SparrowOptimizer" in body and ".solve" in body, "adapter calls SparrowOptimizer::solve")


def static_dense_guard_gate() -> None:
    print("\n=== static dense guard removal gate ===")
    sources = production_sparrow_sources()
    joined = "\n".join(sources.values())
    no_space = re.sub(r"\s+", "", joined)
    guard_patterns = [
        "instances.len()>=100&&sheets.len()==1",
        "instances.len()>=100&&problem.container.sheets.len()==1",
        "large_single_sheet",
        "guarded dense partial",
        "guard marker",
        "BIG_UNSUPPORTED_LOSS;diag.collision_graph_final_pairs=1",
    ]
    for pat in guard_patterns:
        haystack = no_space if " " not in pat and "guard" not in pat else joined.lower()
        needle = pat.lower() if haystack is joined.lower() else pat
        check(needle not in haystack, f"no production dense shortcut/marker pattern: {pat}")
    solve_body = function_body(joined, "solve")
    if solve_body:
        before_state = solve_body.split("SparrowState::new_with_diag", 1)[0]
        check("return SparrowSolveResult" not in before_state, "SparrowOptimizer::solve has no pre-search SparrowSolveResult return")
        check("SparrowCollisionTracker" in solve_body and "final_validation" in solve_body, "solve still performs real tracker/final validation")
    else:
        check(False, "SparrowOptimizer::solve body found")


def run_solver(inp: dict[str, Any], cap: float) -> tuple[dict[str, Any], float]:
    with tempfile.TemporaryDirectory() as tmp:
        ip = Path(tmp) / "input.json"
        op = Path(tmp) / "output.json"
        ip.write_text(json.dumps(inp), encoding="utf-8")
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(BINARY), "--input", str(ip), "--output", str(op)],
                capture_output=True, text=True, timeout=cap,
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


def lv8_input(quantity_by_id: dict[str, int], stocks_qty: int, seed: int, tl: int, name: str) -> tuple[dict[str, Any], int]:
    data = json.loads(LV8_FIXTURE.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in data.get("parts", [])}
    missing = sorted(set(quantity_by_id) - set(by_id))
    if missing:
        raise AssertionError(f"missing LV8 fixture ids: {missing}")
    sheet = data.get("sheet") or {}
    parts = [part_from_fixture(by_id[pid], qty) for pid, qty in quantity_by_id.items() if qty > 0]
    return base(
        parts=parts,
        stocks=[{"id": "LV8_SHEET", "quantity": stocks_qty, "width": float(sheet.get("width_mm", 1500.0)), "height": float(sheet.get("height_mm", 3000.0))}],
        seed=seed,
        tl=tl,
        name=name,
    ), sum(quantity_by_id.values())


def od(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("optimizer_diagnostics") or {}


def cbd(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("collision_backend_diagnostics") or {}


def metrics(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("metrics") or {}


def check_common_runtime(out: dict[str, Any], label: str, require_ok: bool) -> None:
    d = od(out)
    b = cbd(out)
    if require_ok:
        check(out.get("status") == "ok", f"{label}: status ok, got {out.get('status')}")
    else:
        check(out.get("status") in {"ok", "partial"}, f"{label}: status ok/partial, got {out.get('status')}")
    check(d.get("pipeline_used") == "sparrow_cde", f"{label}: pipeline_used sparrow_cde")
    check(d.get("sparrow_native_model_active") is True, f"{label}: native model active")
    check(d.get("sparrow_native_tracker_active") is True, f"{label}: native tracker active")
    check(d.get("sparrow_old_core_used") is False, f"{label}: old core false")
    check((b.get("bbox_fallback_queries") or 0) == 0, f"{label}: no bbox fallback")
    check((d.get("search_position_lbf_fallback_used") or d.get("sparrow_lbf_fallback_used") or 0) == 0, f"{label}: no LBF fallback")
    check((d.get("sparrow_compression_passes") or 0) == 0, f"{label}: compression passes zero")


def runtime_medium_gate() -> None:
    print("\n=== runtime medium CDE gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    inp = base(
        parts=[{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        stocks=[{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        seed=5, tl=30, name="q24r7r1_medium_native_regression",
    )
    out, ms = run_solver(inp, cap=120.0)
    check_common_runtime(out, "medium", require_ok=True)
    placed = int(metrics(out).get("placed_count") or 0)
    d = od(out)
    check(placed == 12, f"medium: placed 12/12, got {placed} ({ms/1000:.1f}s)")
    check(d.get("sparrow_converged") is True, "medium: converged")
    check(d.get("sparrow_collision_graph_final_pairs") == 0, "medium: final pairs 0")
    check(d.get("sparrow_boundary_violations_final") == 0, "medium: boundary 0")


def runtime_lv8_12types_gate() -> None:
    print("\n=== runtime LV8 12 types x1 regression ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    fixture = json.loads(LV8_FIXTURE.read_text(encoding="utf-8"))
    qty = {p["id"]: 1 for p in fixture.get("parts", [])}
    inp, req = lv8_input(qty, stocks_qty=2, seed=11, tl=45, name="q24r7r1_lv8_12types_x1")
    check(req == 12, f"LV8 x1 required 12, got {req}")
    out, ms = run_solver(inp, cap=180.0)
    check_common_runtime(out, "lv8_12types_x1", require_ok=True)
    placed = int(metrics(out).get("placed_count") or 0)
    d = od(out)
    check(placed == req, f"lv8_12types_x1: placed {req}/{req}, got {placed} ({ms/1000:.1f}s)")
    check(d.get("sparrow_collision_graph_final_pairs") == 0, "lv8_12types_x1: final pairs 0")
    check(d.get("sparrow_boundary_violations_final") == 0, "lv8_12types_x1: boundary 0")


def runtime_lv8_reference_sheet1_real_run_gate() -> None:
    print("\n=== runtime LV8 reference sheet 1 real-run gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    req = sum(FIRST_SHEET_QTY.values())
    check(req == 191, f"first-sheet vector totals 191, got {req}")
    inp, req2 = lv8_input(FIRST_SHEET_QTY, stocks_qty=1, seed=17, tl=240, name="q24r7r1_lv8_reference_sheet1_191_real_run")
    check(req2 == 191, f"generated input requires 191, got {req2}")
    out, ms = run_solver(inp, cap=600.0)
    d = od(out)
    b = cbd(out)
    m = metrics(out)
    status = out.get("status")
    placed = int(m.get("placed_count") or 0)
    final_pairs = d.get("sparrow_collision_graph_final_pairs")
    boundary = d.get("sparrow_boundary_violations_final")
    print(f"  [INFO] dense status={status} placed_metric={placed}/191 runtime={ms/1000:.1f}s final_pairs={final_pairs} boundary={boundary}")
    check_common_runtime(out, "lv8_reference_sheet1", require_ok=False)
    # Real-run proof: these must be non-zero for the dense probe.
    check(ms > 1000.0, "dense probe runtime is real (>1s), not 0.0s guarded partial")
    check((d.get("sparrow_iterations") or 0) > 1 or (d.get("exploration_iterations") or 0) > 0, "dense probe has real iterations/exploration")
    check((d.get("sparrow_search_position_calls") or d.get("search_position_calls") or 0) > 0, "dense probe invoked native search")
    check((d.get("sparrow_search_position_samples") or 0) > 0, "dense probe evaluated search samples")
    check((d.get("sparrow_worker_candidates_evaluated") or 0) > 0, "dense probe evaluated worker candidates")
    cde_queries = (b.get("cde_total_queries") or 0) + (d.get("sparrow_severity_probe_queries") or 0) + (d.get("collision_severity_probe_queries") or 0)
    check(cde_queries > 0, f"dense probe used CDE queries ({cde_queries})")
    check(d.get("sparrow_large_single_sheet_guard_used") is not True, "dense guard diagnostic is absent/false")
    check(d.get("sparrow_dense_real_run") is True or ((d.get("sparrow_search_position_calls") or 0) > 0 and cde_queries > 0), "dense real-run diagnostic or equivalent activity proof present")
    check(final_pairs is not None and boundary is not None, "dense probe reports real final pairs/boundary fields")

    if status == "ok" and placed == 191 and final_pairs == 0 and boundary == 0:
        partial(True, "dense fit gate: FULL 191/191 CDE-valid")
    else:
        # Partial is acceptable for this repair only when the real-run gate above passed.
        partial(False, "dense fit gate: not full 191/191 yet; report blockers and unresolved/colliding ids")
        # Enforce honest partial semantics: do not present seed placement count as solved.
        check(status == "partial", "dense unsolved result is explicit partial")
        check(final_pairs != 1 or (d.get("sparrow_search_position_calls") or 0) > 0, "final pair count is not just a pre-search guard marker")
        blocker_fields = [
            "sparrow_dense_partial_reason",
            "sparrow_dense_unresolved_instances",
            "sparrow_dense_colliding_instances",
            "sparrow_dense_blocker_instances",
        ]
        check(any(k in d for k in blocker_fields) or out.get("unplaced"), "partial dense result exposes blocker reason/list or unplaced list")


def main() -> None:
    print("SGH-Q24R7-R1 dense first-sheet real-run fix smoke")
    static_architecture_gate()
    static_dense_guard_gate()
    runtime_medium_gate()
    runtime_lv8_12types_gate()
    runtime_lv8_reference_sheet1_real_run_gate()
    print("\n" + "=" * 72)
    print(f"Results: {PASS} passed, {FAIL} failed, {PARTIAL} partial notes")
    if FAIL:
        print("SMOKE: FAIL")
        sys.exit(1)
    if PARTIAL:
        print("SMOKE: PASS_WITH_DENSE_FIT_PARTIAL")
        sys.exit(0)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
