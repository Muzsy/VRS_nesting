#!/usr/bin/env python3
"""SGH-Q24R9 exact upstream-style tracker/evaluator/search semantics smoke.

This smoke is intentionally stricter than Q24R8. It is designed to fail the
Q24R8 proxy implementation and pass only when the native Sparrow core uses
CDE/hazard-style quantification and tracker-driven evaluator semantics.
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


def partial_note(cond: bool, msg: str) -> None:
    global PASS, PARTIAL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        PARTIAL += 1
        print(f"  [PARTIAL] {msg}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


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
    return sources


def joined_sources() -> str:
    return "\n".join(production_sparrow_sources().values())


def function_body(text: str, fn_name: str) -> str:
    m = re.search(rf"(?:pub\s+)?fn\s+{re.escape(fn_name)}\s*\([^{{]*\{{", text)
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


def struct_body(text: str, name: str) -> str:
    m = re.search(rf"struct\s+{re.escape(name)}\b[^{{]*\{{", text)
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


def static_native_architecture_gate() -> None:
    print("\n=== static native architecture gate ===")
    sources = production_sparrow_sources()
    joined = "\n".join(sources.values())
    check(bool(sources), "production optimizer/sparrow sources exist")
    for token in [
        "SparrowProblem", "SPInstance", "SparrowPlacement", "SparrowLayout",
        "SparrowSolution", "SparrowCollisionTracker", "SparrowOptimizer",
        "LBFBuilder", "SampleEvaluator", "BestSamples", "UniformBBoxSampler",
        "SeparationEvaluator", "LBFEvaluator", "SeparatorWorker", "move_items_multi",
    ]:
        check(token in joined, f"native concept present: {token}")
    for token in [
        "WorkingLayout", "VrsCollisionTracker", "SparrowSeparationKernel",
        "search_position_for_target", "build_constructive_seed_layout",
        "PhaseOptimizer", "MultiSheetManager",
    ]:
        offenders = [str(p.relative_to(ROOT)) for p, txt in sources.items() if token in txt]
        check(not offenders, f"no {token} in production optimizer/sparrow" + (f" ({offenders})" if offenders else ""))
    adapter_body = function_body(strip_tests_and_comments(read(ADAPTER)), "run_sparrow_pipeline")
    check("SparrowProblem" in adapter_body and "from_solver_input" in adapter_body, "adapter constructs native SparrowProblem")
    check("SparrowOptimizer" in adapter_body and ".solve" in adapter_body, "adapter calls SparrowOptimizer::solve")


def static_exact_semantics_gate() -> None:
    print("\n=== static exact tracker/evaluator/search semantics gate ===")
    src = joined_sources()
    pair_body = function_body(src, "quantify_collision_poly_poly_native")
    cont_body = function_body(src, "quantify_collision_poly_container_native")
    sep_struct = struct_body(src, "SeparationEvaluator")
    sep_body = function_body(src, "score_candidate")
    worker_body = function_body(src, "run_worker_pass")
    coord_body = function_body(src, "refine_coord_desc")

    check(pair_body != "", "pair quantification function exists")
    check(cont_body != "", "container quantification function exists")

    forbidden_pair = ["overlap_proxy", "ix * iy", "candidate.max_x.min(fixed.max_x)", "candidate.min_x.max(fixed.min_x)"]
    for token in forbidden_pair:
        check(token not in pair_body, f"pair quantification does not use bbox-overlap proxy token: {token}")
    forbidden_cont = ["outside_proxy", "inside_x", "inside_y", "bbox -", "candidate.max_x.min(sheet.max_x)", "bbox_area(candidate)"]
    for token in forbidden_cont:
        check(token not in cont_body, f"container quantification does not use bbox-outside proxy token: {token}")

    probe_or_hazard_tokens = ["probe_pair", "resolution", "query_pair", "hazard", "quantify_collision"]
    check(any(t in pair_body for t in probe_or_hazard_tokens), "pair quantification uses probe/hazard/CDE-style semantics")
    check(any(t in cont_body for t in ["probe_boundary", "resolution", "query_boundary", "hazard", "container"]), "container quantification uses probe/hazard/CDE-style semantics")

    check("tracker" in sep_struct or "tracker" in sep_body, "SeparationEvaluator has access to tracker/weights")
    check("pair_weight" in sep_body or "weight_for_pair" in sep_body or "tracker.weight" in sep_body, "SeparationEvaluator uses tracker pair weights")
    check("upper_bound" in sep_body, "SeparationEvaluator supports upper-bound pruning")
    check("1.0_f64.max(base).min(base + 1.0)" not in sep_body, "SeparationEvaluator no longer invents local weights from base loss")

    check("new_total < old_total" not in worker_body, "worker acceptance does not use loose new_total fallback")
    check("new_pairs < old_pairs" not in worker_body, "worker acceptance does not use loose new_pairs fallback")
    check("new_w <= old_w" in worker_body or "candidate_weighted" in worker_body or "weighted_loss_for_item" in worker_body, "worker acceptance remains weighted-loss driven")

    # Require a real nonzero rotation delta path in coordinate descent.
    nonzero_dr_pattern = re.search(r"\([^\n\)]*,\s*[^\n\)]*,\s*(?!0\.0\b|0\b)[A-Za-z_][A-Za-z0-9_]*", coord_body)
    check(bool(nonzero_dr_pattern) or "rotation_step" in coord_body or "dr_step" in coord_body, "coordinate descent contains nonzero rotation-wiggle path")
    check("[(step, 0.0, 0.0); 6]" not in coord_body, "coordinate descent no longer degenerates to all-zero rotation axes")

    for token in ["polygon_overlap_surrogate_loss", "polygon_boundary_surrogate_loss", "final_validation_tracker_bounded", "is_dense_reference_case"]:
        check(token not in src, f"forbidden old shortcut absent: {token}")
    check("enable_compression: false" in src or "compression_passes" in src, "compression remains explicitly controlled/disabled")


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


def base(parts: list[dict[str, Any]], stocks: list[dict[str, Any]], seed: int, tl: int, name: str, rotation_policy: str = "orthogonal") -> dict[str, Any]:
    return {
        "contract_version": "v1",
        "project_name": name,
        "seed": seed,
        "time_limit_s": tl,
        "solver_profile": PROFILE,
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "rotation_policy": rotation_policy,
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


def common_runtime(out: dict[str, Any], label: str, require_ok: bool) -> None:
    d = od(out); b = cbd(out)
    if require_ok:
        check(out.get("status") == "ok", f"{label}: status ok, got {out.get('status')}")
    else:
        check(out.get("status") in {"ok", "partial"}, f"{label}: status ok/partial, got {out.get('status')}")
    check(d.get("pipeline_used") == "sparrow_cde", f"{label}: pipeline_used sparrow_cde")
    check(d.get("sparrow_native_model_active") is True, f"{label}: native model active")
    check(d.get("sparrow_native_tracker_active") is True, f"{label}: native tracker active")
    check(d.get("sparrow_old_core_used") is False, f"{label}: old core false")
    check((b.get("bbox_fallback_queries") or 0) == 0, f"{label}: no bbox fallback")
    check((d.get("sparrow_compression_passes") or 0) == 0, f"{label}: compression passes zero")


def runtime_medium_gate() -> None:
    print("\n=== runtime medium CDE gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    inp = base(
        parts=[{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        stocks=[{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        seed=5, tl=30, name="q24r9_medium_native_regression",
    )
    out, ms = run_solver(inp, cap=120.0)
    common_runtime(out, "medium", True)
    placed = int(metrics(out).get("placed_count") or 0)
    d = od(out)
    check(placed == 12, f"medium: placed 12/12, got {placed} ({ms/1000:.1f}s)")
    check(d.get("sparrow_collision_graph_final_pairs") == 0, "medium: final pairs 0")
    check(d.get("sparrow_boundary_violations_final") == 0, "medium: boundary 0")


def runtime_lv8_12types_gate() -> None:
    print("\n=== runtime LV8 12 types x1 regression ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    fixture = json.loads(LV8_FIXTURE.read_text(encoding="utf-8"))
    qty = {p["id"]: 1 for p in fixture.get("parts", [])}
    inp, req = lv8_input(qty, stocks_qty=2, seed=11, tl=45, name="q24r9_lv8_12types_x1")
    out, ms = run_solver(inp, cap=180.0)
    common_runtime(out, "lv8_12types_x1", True)
    placed = int(metrics(out).get("placed_count") or 0)
    d = od(out)
    check(req == 12 and placed == 12, f"lv8_12types_x1: placed 12/12, got {placed}/{req} ({ms/1000:.1f}s)")
    check(d.get("sparrow_collision_graph_final_pairs") == 0, "lv8_12types_x1: final pairs 0")
    check(d.get("sparrow_boundary_violations_final") == 0, "lv8_12types_x1: boundary 0")


def runtime_rotation_wiggle_static_or_micro_gate() -> None:
    print("\n=== rotation wiggle evidence gate ===")
    # Static proof is mandatory; runtime diagnostic is optional because the public
    # schema may not yet expose continuous rotation. The implementation should
    # also add a Rust unit test or diagnostic that this smoke can detect.
    src = joined_sources()
    coord_body = function_body(src, "refine_coord_desc")
    check("rotation" in coord_body.lower(), "coord descent references rotation")
    check("rotation_step" in src or "dr_step" in src or "search_rotation_wiggle" in src, "rotation wiggle variable/diagnostic exists")
    check("0.0);" not in coord_body or "rotation_step" in coord_body or "dr_step" in coord_body, "coord descent is not hard-coded to zero rotation only")


def runtime_lv8_reference_sheet1_gate() -> None:
    print("\n=== runtime LV8 reference sheet 1 exact-semantics progress gate ===")
    if not BINARY.exists():
        check(False, f"binary exists at {BINARY}; run cargo build --release first")
        return
    req = sum(FIRST_SHEET_QTY.values())
    check(req == 191, f"first-sheet vector totals 191, got {req}")
    inp, req2 = lv8_input(FIRST_SHEET_QTY, stocks_qty=1, seed=17, tl=90, name="q24r9_lv8_reference_sheet1_191_exact_semantics")
    check(req2 == 191, f"generated input requires 191, got {req2}")
    out, ms = run_solver(inp, cap=240.0)
    d = od(out); b = cbd(out); m = metrics(out)
    status = out.get("status")
    placed = int(m.get("placed_count") or 0)
    initial_raw = d.get("sparrow_initial_raw_loss")
    final_raw = d.get("sparrow_final_raw_loss")
    initial_pairs = d.get("sparrow_collision_graph_initial_pairs")
    final_pairs = d.get("sparrow_collision_graph_final_pairs")
    validated = d.get("sparrow_dense_validated_placements") or 0
    boundary = d.get("sparrow_boundary_violations_final")
    search_calls = d.get("sparrow_search_position_calls") or 0
    search_samples = d.get("sparrow_search_position_samples") or 0
    worker_evals = d.get("sparrow_worker_candidates_evaluated") or 0
    accepted_moves = d.get("sparrow_moves_accepted") or 0
    pair_quant = d.get("sparrow_quantified_pair_queries") or d.get("quantified_pair_queries") or 0
    boundary_quant = d.get("sparrow_quantified_boundary_queries") or d.get("quantified_boundary_queries") or 0
    print(f"  [INFO] dense status={status} placed_metric={placed}/191 runtime={ms/1000:.1f}s initial_raw={initial_raw} final_raw={final_raw} initial_pairs={initial_pairs} final_pairs={final_pairs} validated={validated} boundary={boundary} search_calls={search_calls} samples={search_samples} worker_evals={worker_evals} accepted={accepted_moves} pair_quant={pair_quant} boundary_quant={boundary_quant}")
    common_runtime(out, "lv8_reference_sheet1", False)
    check(ms > 1000.0, "dense probe runtime is real (>1s), not guarded partial")
    check(search_calls > 0 and search_samples > 0 and worker_evals > 0, "dense probe has real search/worker activity")
    check(accepted_moves > 0, "dense probe accepts at least one move")
    cde_activity = (b.get("cde_batch_candidate_queries") or 0) + (b.get("cde_batch_collisions_returned") or 0)
    check(cde_activity > 100, f"dense probe used CDE activity ({cde_activity})")
    check(initial_raw is not None and final_raw is not None and final_raw < initial_raw, "dense final raw loss improves over seed")
    check(initial_pairs is not None and final_pairs is not None and final_pairs < initial_pairs, "dense final pairs improve over seed")
    check(validated > 39, f"dense validated placements beats Q24R8 baseline 39 (got {validated})")
    # Strong target: may remain partial, but should improve meaningfully or document blocker.
    partial_note(final_pairs is not None and final_pairs <= 120, f"dense target final pairs <=120 (got {final_pairs})")
    partial_note(validated >= 60, f"dense target validated placements >=60 (got {validated})")
    if status != "ok":
        check(status == "partial", "dense unsolved result is explicit partial")
        check(bool(d.get("sparrow_dense_partial_reason")), "partial dense result exposes reason")
        check(bool(d.get("sparrow_dense_unresolved_instances")), "partial dense result exposes unresolved ids")


def main() -> None:
    print("SGH-Q24R9 exact upstream-style tracker/evaluator/search semantics smoke")
    static_native_architecture_gate()
    static_exact_semantics_gate()
    runtime_medium_gate()
    runtime_lv8_12types_gate()
    runtime_rotation_wiggle_static_or_micro_gate()
    runtime_lv8_reference_sheet1_gate()
    print("\n" + "=" * 72)
    print(f"Results: {PASS} passed, {FAIL} failed, {PARTIAL} partial notes")
    if FAIL:
        print("SMOKE: FAIL")
        sys.exit(1)
    if PARTIAL:
        print("SMOKE: PASS_WITH_EXPLICIT_191_PARTIAL")
        sys.exit(0)
    print("SMOKE: PASS")


if __name__ == "__main__":
    main()
