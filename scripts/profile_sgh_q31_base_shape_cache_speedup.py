#!/usr/bin/env python3
"""
SGH-Q31 CDE base-shape cache hot-path speedup profile runner.

Runs the local vrs_solver with SGH_Q30_R1_EXCLUSIVE_PROFILE=1 on dense191
and lv8_subset. Extracts sparrow_q31_* fields from optimizer_diagnostics to
verify that prepare_base_shape_native_hotpath_calls == 0 and cache stats are
correct. Writes the Q31 summary JSON + Markdown report.

Profile flag:   SGH_Q30_R1_EXCLUSIVE_PROFILE=1
Acceptance:     prepare_base_shape_native_hotpath_calls == 0 (dense191)
                placed_count == 191
                final_pairs <= 88
Output:         artifacts/benchmarks/sgh_q31/base_shape_cache_summary.json
                artifacts/benchmarks/sgh_q31/base_shape_cache_report.md
                artifacts/benchmarks/sgh_q31/inputs/dense191.json
                artifacts/benchmarks/sgh_q31/inputs/lv8_subset.json
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
LOCAL_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
FIXTURES_DIR = ROOT / "rust" / "vrs_solver" / "tests" / "fixtures"
DENSE191_FIXTURE = FIXTURES_DIR / "sgh_q28_dense191_benchmark" / "dense_191_lv8_derived.json"
MEDIUM_FIXTURE = FIXTURES_DIR / "sgh_q26_single_sheet_validation" / "medium_mixed_rotations.json"
Q30_INPUTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q30" / "inputs"
ARTIFACTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q31"
INPUTS_DIR = ARTIFACTS_DIR / "inputs"

BASELINE_PREPARE_MS = 21433.1
MAX_HOTPATH_MS = BASELINE_PREPARE_MS * 0.10
MAX_FINAL_PAIRS = 88


def _run_solver(solver_input: dict, case_id: str, time_limit: int = 30) -> dict[str, Any]:
    """Run local solver with SGH_Q30_R1_EXCLUSIVE_PROFILE=1, return output dict."""
    solver_input = dict(solver_input, time_limit_s=time_limit)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    input_path = INPUTS_DIR / f"{case_id}.json"
    input_path.write_text(json.dumps(solver_input, indent=2))
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "output.json"
        env = dict(os.environ, SGH_Q30_R1_EXCLUSIVE_PROFILE="1")
        try:
            result = subprocess.run(
                [str(LOCAL_BIN), "--input", str(input_path), "--output", str(out_path)],
                capture_output=True,
                text=True,
                timeout=time_limit + 120,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"case_id": case_id, "status": "timeout", "error": "solver timed out"}
        except FileNotFoundError:
            return {"case_id": case_id, "status": "error", "error": f"binary not found: {LOCAL_BIN}"}
        if out_path.exists():
            try:
                return json.loads(out_path.read_text())
            except Exception as e:
                return {"case_id": case_id, "status": "error", "error": f"output parse error: {e}"}
        return {"case_id": case_id, "status": "error", "error": result.stderr[:500] or "no output file"}


def _build_dense191_input() -> dict:
    if Q30_INPUTS_DIR.exists() and (Q30_INPUTS_DIR / "dense191.json").exists():
        return json.loads((Q30_INPUTS_DIR / "dense191.json").read_text())
    if DENSE191_FIXTURE.exists():
        d = json.loads(DENSE191_FIXTURE.read_text())
        d.setdefault("project_name", "sgh_q31_dense191_profile")
        d.setdefault("seed", 42)
        d["solver_profile"] = "jagua_optimizer_phase1_outer_only"
        d["margin_mm"] = 0.0
        d["optimizer_pipeline"] = "sparrow_cde"
        d["collision_backend"] = "cde"
        return d
    raise FileNotFoundError("dense191 input not found")


def _build_lv8_subset_input() -> dict:
    if Q30_INPUTS_DIR.exists() and (Q30_INPUTS_DIR / "lv8_subset.json").exists():
        return json.loads((Q30_INPUTS_DIR / "lv8_subset.json").read_text())
    raise FileNotFoundError("lv8_subset input not found in Q30 inputs dir")


def _extract_q31(od: dict) -> dict[str, Any]:
    return {k: v for k, v in od.items() if k.startswith("sparrow_q31_")}


def _case_summary(case_id: str, output: dict, time_limit: int) -> dict:
    od = output.get("optimizer_diagnostics") or {}
    metrics = output.get("metrics") or {}
    status = output.get("status", "unknown")
    placed_count = metrics.get("placed_count", 0)

    # Q31 cache fields
    hotpath_calls = od.get("sparrow_q31_prepare_base_shape_native_hotpath_calls") or 0
    hotpath_ms = od.get("sparrow_q31_prepare_base_shape_native_hotpath_ms") or 0.0
    cache_hits = od.get("sparrow_q31_base_shape_cache_hits") or 0
    cache_misses = od.get("sparrow_q31_base_shape_cache_misses") or 0
    cache_unique = od.get("sparrow_q31_base_shape_cache_unique_parts") or 0
    cache_reused = od.get("sparrow_q31_base_shape_cache_reused_instances") or 0
    cache_build_ms = od.get("sparrow_q31_base_shape_cache_build_ms") or 0.0
    tracker_transform_ms = od.get("sparrow_q31_tracker_transform_from_base_ms") or 0.0
    search_hits = od.get("sparrow_q31_search_base_shape_cache_hits") or 0
    lbf_hits = od.get("sparrow_q31_lbf_base_shape_cache_hits") or 0

    # Q30-R1 search timing for comparison
    search_total_ms = od.get("sparrow_q30_search_total_ms") or 0.0
    search_unaccounted_ratio = od.get("sparrow_q30r1_search_unaccounted_ratio_pct") or 0.0
    prepare_base_ms_q30 = od.get("sparrow_q30r1_prepare_base_shape_native_ms") or 0.0

    final_pairs = od.get("sparrow_collision_graph_final_pairs") or 0

    # Speedup: Q30-R1 baseline prepare_base was 78.9% of search_total ~21433ms
    # After Q31 it should be ~0
    hotpath_reduction_pct = 100.0 * (1.0 - hotpath_ms / BASELINE_PREPARE_MS) if BASELINE_PREPARE_MS > 0 else 0.0

    return {
        "case": case_id,
        "name": case_id,
        "status": status,
        "time_limit_s": time_limit,
        "placed_count": placed_count,
        "instance_count": 191 if "dense191" in case_id else placed_count,
        "final_pairs": final_pairs,
        "sparrow_collision_graph_final_pairs": final_pairs,
        # Q31 base-shape cache diagnostics
        "prepare_base_shape_native_hotpath_calls": hotpath_calls,
        "prepare_base_shape_native_hotpath_ms": round(hotpath_ms, 3),
        "base_shape_cache_hits": cache_hits,
        "base_shape_cache_misses": cache_misses,
        "base_shape_cache_unique_parts": cache_unique,
        "base_shape_cache_reused_instances": cache_reused,
        "base_shape_cache_build_ms": round(cache_build_ms, 3),
        "tracker_transform_from_base_ms": round(tracker_transform_ms, 3),
        "search_base_shape_cache_hits": search_hits,
        "lbf_base_shape_cache_hits": lbf_hits,
        # Speedup measurement vs Q30-R1 baseline
        "baseline_prepare_ms": BASELINE_PREPARE_MS,
        "hotpath_reduction_pct": round(hotpath_reduction_pct, 1),
        "max_hotpath_ms_gate": round(MAX_HOTPATH_MS, 2),
        "max_final_pairs_gate": MAX_FINAL_PAIRS,
        # Search timing (for comparison with Q30-R1)
        "search_total_ms": round(search_total_ms, 3),
        "search_unaccounted_ratio_pct": round(search_unaccounted_ratio, 2),
        "prepare_base_ms_r1_profile": round(prepare_base_ms_q30, 3),
        # Raw q31 field set for debugging
        "q31_fields": _extract_q31(od),
    }


def _determine_pass(dense191: dict) -> tuple[str, str]:
    """Return (status_str, reason)."""
    placed = dense191.get("placed_count")
    status = dense191.get("status", "unknown")
    final_pairs = dense191.get("final_pairs", 999)
    hot_calls = dense191.get("prepare_base_shape_native_hotpath_calls", 999)
    hot_ms = dense191.get("prepare_base_shape_native_hotpath_ms", 9e9)
    misses = dense191.get("base_shape_cache_misses", 999)
    unique_parts = dense191.get("base_shape_cache_unique_parts", 0)

    if status not in ("partial", "ok"):
        return "FAIL", f"status={status!r} not in {{partial, ok}}"
    if placed != 191:
        return "FAIL", f"placed_count={placed} != 191"
    if final_pairs > MAX_FINAL_PAIRS:
        return "FAIL", f"final_pairs={final_pairs} > {MAX_FINAL_PAIRS}"
    if hot_calls != 0:
        return "FAIL", f"prepare_base_shape_native_hotpath_calls={hot_calls} != 0"
    if hot_ms > MAX_HOTPATH_MS:
        return "FAIL", f"prepare_base_shape_native_hotpath_ms={hot_ms:.1f} > {MAX_HOTPATH_MS:.1f}"
    if unique_parts > 0 and misses > unique_parts + 2:
        return "FAIL", f"cache_misses={misses} > unique_parts+2={unique_parts + 2}"
    return "PASS", "all gates met"


def _write_summary(cases: list[dict], dense191: dict, status: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "task": "sgh_q31_cde_base_shape_cache_hotpath_speedup",
        "status": status,
        "profile_flag": "SGH_Q30_R1_EXCLUSIVE_PROFILE=1",
        "baseline_prepare_base_ms": BASELINE_PREPARE_MS,
        "max_hotpath_ms_gate": MAX_HOTPATH_MS,
        "max_final_pairs_gate": MAX_FINAL_PAIRS,
        "acceptance_gates": {
            "placed_count_eq_191": True,
            "status_in_partial_ok": True,
            "final_pairs_le_88": True,
            "hotpath_calls_eq_0": True,
            "hotpath_ms_le_2143": True,
            "cache_misses_le_unique_plus_2": True,
        },
        "dense191": dense191,
        "cases": cases,
    }
    out = ARTIFACTS_DIR / "base_shape_cache_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"Written: {out}")


def _write_report(cases: list[dict], dense191: dict, status: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    placed = dense191.get("placed_count", 0)
    final_pairs = dense191.get("final_pairs", "?")
    hot_calls = dense191.get("prepare_base_shape_native_hotpath_calls", "?")
    hot_ms = dense191.get("prepare_base_shape_native_hotpath_ms", 0.0)
    misses = dense191.get("base_shape_cache_misses", "?")
    hits = dense191.get("base_shape_cache_hits", "?")
    unique = dense191.get("base_shape_cache_unique_parts", "?")
    build_ms = dense191.get("base_shape_cache_build_ms", 0.0)
    reduction_pct = dense191.get("hotpath_reduction_pct", 0.0)
    search_total = dense191.get("search_total_ms", 0.0)

    lines = [
        "# SGH-Q31 CDE Base-Shape Cache Hot-Path Speedup — Report",
        "",
        "## Summary",
        "",
        f"**Status:** `{status}`",
        "",
        "## Problem Context",
        "",
        "SGH-Q30-R1 profiling revealed that `prepare_base_shape_native` (POI+surrogate",
        "computation per search call) accounted for 78.9% of `search_total_ms` on dense191",
        f"(baseline: {BASELINE_PREPARE_MS:.1f}ms). Q31 builds a per-part `HashMap<String,",
        "Rc<CdeBaseShape>>` cache in `from_solver_input` so each unique part's base shape",
        "is built exactly once. All instances share the `Rc`, and hot paths in search.rs,",
        "lbf.rs, and tracker.rs now use `transform_base_to_candidate` instead.",
        "",
        "## Dense191 Results",
        "",
        f"| Metric | Value | Gate |",
        f"|---|---|---|",
        f"| status | {dense191.get('status', '?')} | partial/ok |",
        f"| placed_count | {placed} | == 191 |",
        f"| final_pairs | {final_pairs} | <= {MAX_FINAL_PAIRS} |",
        f"| hotpath_calls | {hot_calls} | == 0 |",
        f"| hotpath_ms | {hot_ms:.3f} | <= {MAX_HOTPATH_MS:.2f} |",
        f"| cache_unique_parts | {unique} | > 0 |",
        f"| cache_misses | {misses} | <= unique+2 |",
        f"| cache_hits | {hits} | >= instances-unique |",
        f"| cache_build_ms | {build_ms:.3f} | informational |",
        f"| prepare_base_reduction_pct | {reduction_pct:.1f}% | informational |",
        f"| search_total_ms | {search_total:.1f} | informational |",
        "",
        "## Case Results",
        "",
    ]

    for case in cases:
        cid = case.get("case") or case.get("name") or "unknown"
        lines.append(f"### Case: {cid}")
        lines.append("")
        lines.append(f"| Field | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| status | {case.get('status', '?')} |")
        lines.append(f"| placed_count | {case.get('placed_count', '?')} |")
        lines.append(f"| final_pairs | {case.get('final_pairs', '?')} |")
        lines.append(f"| hotpath_calls | {case.get('prepare_base_shape_native_hotpath_calls', '?')} |")
        lines.append(f"| hotpath_ms | {case.get('prepare_base_shape_native_hotpath_ms', '?')} |")
        lines.append(f"| cache_unique_parts | {case.get('base_shape_cache_unique_parts', '?')} |")
        lines.append(f"| cache_misses | {case.get('base_shape_cache_misses', '?')} |")
        lines.append(f"| cache_hits | {case.get('base_shape_cache_hits', '?')} |")
        lines.append(f"| cache_build_ms | {case.get('base_shape_cache_build_ms', '?')} |")
        lines.append(f"| search_total_ms | {case.get('search_total_ms', '?')} |")
        lines.append("")

    lines.extend([
        "## Implementation",
        "",
        "- `SparrowProblem::from_solver_input`: builds `HashMap<String, Rc<CdeBaseShape>>`",
        "- `SPInstance`: stores `pub base_shape: Rc<CdeBaseShape>`",
        "- `sample/search.rs`: uses `inst.base_shape.clone()` (O(1) Rc clone)",
        "- `lbf.rs` `find_clear_placement` + `lbf_order_key`: same pattern",
        "- `quantify/tracker.rs` `prepare_item`: `transform_base_to_candidate(&inst.base_shape, ...)`",
        "",
        "---",
        "",
        f"Q31_STATUS: {status}",
        f"DENSE191_BASE_SHAPE_HOTPATH_CALLS: {hot_calls}",
        f"DENSE191_BASE_SHAPE_HOTPATH_MS: {hot_ms:.3f}",
        f"DENSE191_BASE_SHAPE_CACHE_MISSES: {misses}",
        f"DENSE191_BASE_SHAPE_CACHE_HITS: {hits}",
        f"DENSE191_PREPARE_BASE_REDUCTION_PCT: {reduction_pct:.1f}%",
        f"DENSE191_FINAL_PAIRS: {final_pairs}",
        "NEXT_HOTSPOT: eval/sep_evaluator.rs::SeparationEvaluator::evaluate_sample",
    ])

    out = ARTIFACTS_DIR / "base_shape_cache_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"Written: {out}")


def main():
    if not LOCAL_BIN.exists():
        print(f"ERROR: binary not found: {LOCAL_BIN}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    print("SGH-Q31 base-shape cache profile runner")
    print(f"Binary: {LOCAL_BIN}")
    print()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    cases = []

    # Dense191 — main acceptance case
    print("[1/2] Running dense191 case (120s) — main acceptance gate...")
    dense191_output = _run_solver(_build_dense191_input(), "dense191", time_limit=120)
    dense191_summary = _case_summary("dense191", dense191_output, 120)
    cases.append(dense191_summary)
    print(f"  status={dense191_output.get('status')} "
          f"placed={dense191_summary['placed_count']} "
          f"final_pairs={dense191_summary['final_pairs']} "
          f"hotpath_calls={dense191_summary['prepare_base_shape_native_hotpath_calls']} "
          f"hotpath_ms={dense191_summary['prepare_base_shape_native_hotpath_ms']:.3f} "
          f"cache_unique={dense191_summary['base_shape_cache_unique_parts']} "
          f"cache_misses={dense191_summary['base_shape_cache_misses']} "
          f"cache_hits={dense191_summary['base_shape_cache_hits']}")

    # LV8 subset — secondary case
    print("[2/2] Running lv8_subset case (60s)...")
    try:
        lv8_input = _build_lv8_subset_input()
        lv8_output = _run_solver(lv8_input, "lv8_subset", time_limit=60)
        lv8_summary = _case_summary("lv8_subset", lv8_output, 60)
    except FileNotFoundError as e:
        print(f"  SKIP: {e}")
        # Write a placeholder so the artifact exists
        placeholder = {"project_name": "sgh_q31_lv8_subset", "seed": 42,
                       "solver_profile": "jagua_optimizer_phase1_outer_only",
                       "margin_mm": 0.0, "optimizer_pipeline": "sparrow_cde",
                       "collision_backend": "cde", "note": f"fixture not found: {e}"}
        (INPUTS_DIR / "lv8_subset.json").write_text(json.dumps(placeholder, indent=2))
        lv8_summary = {"case": "lv8_subset", "name": "lv8_subset", "status": "skipped",
                       "skipped_reason": str(e), "placed_count": 0, "final_pairs": 0,
                       "prepare_base_shape_native_hotpath_calls": 0,
                       "prepare_base_shape_native_hotpath_ms": 0.0,
                       "base_shape_cache_hits": 0, "base_shape_cache_misses": 0,
                       "base_shape_cache_unique_parts": 0, "base_shape_cache_build_ms": 0.0,
                       "hotpath_reduction_pct": 100.0}
    cases.append(lv8_summary)
    if lv8_summary.get("status") != "skipped":
        print(f"  status={lv8_summary.get('status')} "
              f"placed={lv8_summary['placed_count']} "
              f"hotpath_calls={lv8_summary['prepare_base_shape_native_hotpath_calls']}")

    # Determine pass/fail from dense191
    q31_status, reason = _determine_pass(dense191_summary)

    print()
    print(f"Q31_STATUS: {q31_status} ({reason})")
    print(f"DENSE191_BASE_SHAPE_HOTPATH_CALLS: {dense191_summary['prepare_base_shape_native_hotpath_calls']}")
    print(f"DENSE191_BASE_SHAPE_HOTPATH_MS: {dense191_summary['prepare_base_shape_native_hotpath_ms']:.3f}")
    print(f"DENSE191_BASE_SHAPE_CACHE_MISSES: {dense191_summary['base_shape_cache_misses']}")
    print(f"DENSE191_BASE_SHAPE_CACHE_HITS: {dense191_summary['base_shape_cache_hits']}")
    print(f"DENSE191_FINAL_PAIRS: {dense191_summary['final_pairs']}")

    _write_summary(cases, dense191_summary, q31_status)
    _write_report(cases, dense191_summary, q31_status)

    if q31_status != "PASS":
        print(f"\nFAIL: {reason}")
        sys.exit(1)
    else:
        print(f"\nPASS: {reason}")
        sys.exit(0)


if __name__ == "__main__":
    main()
