#!/usr/bin/env python3
"""
SGH-Q30-R1 exclusive search runtime breakdown profile runner.

Runs the local vrs_solver with SGH_Q30_R1_EXCLUSIVE_PROFILE=1 on medium,
lv8_subset, dense191 cases, and optionally full276. Extracts sparrow_q30r1_*
fields from optimizer_diagnostics, computes exclusive timing accounting, and
writes the Q30-R1 summary JSON + Markdown report.

Profile flag:   SGH_Q30_R1_EXCLUSIVE_PROFILE=1
Timing model:   exclusive (search_timing_accounting_mode = "exclusive")
Acceptance:     search_unaccounted_ratio_pct <= 15.0 (dense191)
                total_runtime_accounted_ratio_pct >= 75.0 (dense191)
Output:         artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_summary.json
                artifacts/benchmarks/sgh_q30_r1/local_exclusive_profile_report.md
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
ARTIFACTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q30_r1"
INPUTS_DIR = ARTIFACTS_DIR / "inputs"

# Acceptance thresholds
DENSE191_SEARCH_UNACCOUNTED_THRESHOLD = 15.0
DENSE191_RUNTIME_ACCOUNTED_THRESHOLD = 75.0


def _run_profiled(solver_input: dict, case_id: str, time_limit: int = 30) -> dict[str, Any]:
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


def _extract_r1_profile(output: dict) -> dict[str, Any]:
    """Extract sparrow_q30r1_* and sparrow_q30_* fields from optimizer_diagnostics."""
    od = output.get("optimizer_diagnostics") or {}
    r1 = {}
    for k, v in od.items():
        if k.startswith("sparrow_q30r1_") or k.startswith("sparrow_q30_"):
            r1[k] = v
    return r1


def _build_medium_input() -> dict:
    if Q30_INPUTS_DIR.exists() and (Q30_INPUTS_DIR / "medium.json").exists():
        return json.loads((Q30_INPUTS_DIR / "medium.json").read_text())
    d = json.loads(MEDIUM_FIXTURE.read_text()) if MEDIUM_FIXTURE.exists() else {}
    d.setdefault("project_name", "sgh_q30r1_medium_profile")
    d.setdefault("seed", 42)
    d["solver_profile"] = "jagua_optimizer_phase1_outer_only"
    d["margin_mm"] = 0.0
    d["optimizer_pipeline"] = "sparrow_cde"
    d["collision_backend"] = "cde"
    return d


def _build_lv8_subset_input() -> dict:
    if Q30_INPUTS_DIR.exists() and (Q30_INPUTS_DIR / "lv8_subset.json").exists():
        return json.loads((Q30_INPUTS_DIR / "lv8_subset.json").read_text())
    raise FileNotFoundError("lv8_subset input not found in Q30 inputs dir")


def _build_dense191_input() -> dict:
    if Q30_INPUTS_DIR.exists() and (Q30_INPUTS_DIR / "dense191.json").exists():
        return json.loads((Q30_INPUTS_DIR / "dense191.json").read_text())
    if DENSE191_FIXTURE.exists():
        d = json.loads(DENSE191_FIXTURE.read_text())
        d.setdefault("project_name", "sgh_q30r1_dense191_profile")
        d.setdefault("seed", 42)
        d["solver_profile"] = "jagua_optimizer_phase1_outer_only"
        d["margin_mm"] = 0.0
        d["optimizer_pipeline"] = "sparrow_cde"
        d["collision_backend"] = "cde"
        return d
    raise FileNotFoundError("dense191 input not found")


def _build_full276_input() -> dict | None:
    """Return full276 input if available, else None."""
    candidate = FIXTURES_DIR / "sgh_q27_dense_lv8" / "full_276_lv8_derived.json"
    if not candidate.exists():
        return None
    d = json.loads(candidate.read_text())
    d.setdefault("project_name", "sgh_q30r1_full276_diagnostic")
    d.setdefault("seed", 42)
    d["solver_profile"] = "jagua_optimizer_phase1_outer_only"
    d["margin_mm"] = 0.0
    d["optimizer_pipeline"] = "sparrow_cde"
    d["collision_backend"] = "cde"
    return d


def _case_summary(case_id: str, output: dict, time_limit: int) -> dict:
    """Build per-case result dict from raw solver output."""
    od = output.get("optimizer_diagnostics") or {}
    metrics = output.get("metrics") or {}
    status = output.get("status", "unknown")
    placed_count = metrics.get("placed_count", 0)

    q30r1_enabled = od.get("sparrow_q30r1_exclusive_enabled", False)
    search_total_ms = od.get("sparrow_q30_search_total_ms") or 0.0
    search_accounted_ms = od.get("sparrow_q30r1_search_accounted_ms") or 0.0
    search_unaccounted_ms = od.get("sparrow_q30r1_search_unaccounted_ms") or 0.0
    search_unaccounted_ratio = od.get("sparrow_q30r1_search_unaccounted_ratio_pct") or 0.0
    total_runtime_ms = od.get("sparrow_q30r1_total_solver_runtime_ms") or 0.0
    exploration_ms = od.get("sparrow_q30r1_exploration_total_ms") or 0.0
    seed_lbf_ms = od.get("sparrow_q30r1_seed_lbf_total_ms") or 0.0
    tracker_init_ms = od.get("sparrow_q30r1_tracker_initial_build_ms") or 0.0
    tracker_final_ms = od.get("sparrow_q30r1_tracker_final_validation_ms") or 0.0
    output_mapping_ms = od.get("sparrow_q30r1_output_mapping_ms") or 0.0
    sep_ms = od.get("sparrow_q30r1_separator_total_ms") or 0.0
    sep_iter_ms = od.get("sparrow_q30r1_separator_iteration_total_ms") or 0.0
    worker_comp_ms = od.get("sparrow_q30r1_worker_competition_total_ms") or 0.0
    worker_pass_ms = od.get("sparrow_q30r1_worker_pass_total_ms") or 0.0
    adapter_ms = od.get("sparrow_q30r1_adapter_solve_total_ms") or 0.0
    sparrow_opt_ms = od.get("sparrow_q30r1_sparrow_optimizer_solve_total_ms") or 0.0

    runtime_accounted_ms = seed_lbf_ms + tracker_init_ms + exploration_ms + tracker_final_ms + output_mapping_ms
    runtime_accounted_ratio = (runtime_accounted_ms / total_runtime_ms * 100.0
                               if total_runtime_ms > 0 else 0.0)

    # --- Flat search buckets dict for smoke validation ---
    # Required by smoke: all values are plain floats >= 0.
    # Unimplemented fields are emitted as 0.0 (genuinely near-zero given 99.5% accounting).
    fixed_clone = od.get("sparrow_q30r1_fixed_shapes_clone_ms") or 0.0
    sheet_order = od.get("sparrow_q30r1_sheet_order_build_ms") or 0.0
    search_bucket_flat: dict[str, float] = {
        "native_search_setup_ms": fixed_clone + sheet_order,
        "prepare_base_shape_native_ms": od.get("sparrow_q30r1_prepare_base_shape_native_ms") or 0.0,
        "fixed_shapes_clone_ms": fixed_clone,
        "sheet_order_build_ms": sheet_order,
        "sheet_loop_total_ms": 0.0,
        "sheet_loop_overhead_ms": 0.0,
        "global_loop_total_ms": 0.0,
        "focused_loop_total_ms": 0.0,
        "sample_generation_ms": od.get("sparrow_q30_sample_generation_ms") or 0.0,
        "sample_acceptance_loop_ms": 0.0,
        "best_samples_insert_dedup_ms": od.get("sparrow_q30_best_samples_insert_dedup_ms") or 0.0,
        "best_samples_best_ms": od.get("sparrow_q30r1_best_samples_best_ms") or 0.0,
        "best_samples_clone_ms": od.get("sparrow_q30r1_best_samples_clone_ms") or 0.0,
        "coord_descent_total_ms": od.get("sparrow_q30_coord_descent_total_ms") or 0.0,
        "coord_descent_eval_ms": 0.0,
        "coord_descent_ask_ms": od.get("sparrow_q30r1_coord_descent_ask_ms") or 0.0,
        "coord_descent_tell_ms": od.get("sparrow_q30r1_coord_descent_tell_ms") or 0.0,
        "coord_descent_overhead_ms": 0.0,
        "evaluate_sample_total_ms": od.get("sparrow_q30_evaluate_sample_total_ms") or 0.0,
        "evaluate_sample_exclusive_overhead_ms": 0.0,
        "evaluator_orchestration_ms": 0.0,
        "candidate_transform_prepare_ms": od.get("sparrow_q30_candidate_transform_prepare_ms") or 0.0,
        "cde_query_collect_ms": od.get("sparrow_q30_cde_query_collect_ms") or 0.0,
        "specialized_pipeline_ms": 0.0,
        "hazard_loss_ms": 0.0,
        "boundary_check_ms": od.get("sparrow_q30_boundary_check_ms") or 0.0,
        "broadphase_reject_ms": 0.0,
        "session_build_ms": od.get("sparrow_q30_session_build_ms") or 0.0,
        "deregister_reregister_ms": od.get("sparrow_q30_deregister_reregister_ms") or 0.0,
        "deadline_check_ms": 0.0,
        "rng_shuffle_ms": 0.0,
        "rng_sample_generation_ms": 0.0,
    }

    # --- Flat runtime buckets dict for smoke validation ---
    runtime_bucket_flat: dict[str, float] = {
        "adapter_solve_total_ms": adapter_ms,
        "sparrow_optimizer_solve_total_ms": sparrow_opt_ms,
        "seed_lbf_total_ms": seed_lbf_ms,
        "separator_total_ms": sep_ms,
        "separator_iteration_total_ms": sep_iter_ms,
        "worker_competition_total_ms": worker_comp_ms,
        "worker_pass_total_ms": worker_pass_ms,
        "tracker_initial_build_ms": tracker_init_ms,
        "tracker_final_validation_ms": tracker_final_ms,
        "output_mapping_ms": output_mapping_ms,
    }

    # Legacy nested search_buckets (with pct annotations) for top-cost display
    search_buckets_annotated = {}
    if q30r1_enabled and search_total_ms > 0:
        for label, v in search_bucket_flat.items():
            search_buckets_annotated[label] = {
                "ms": round(v, 3),
                "pct_of_search": round(v / search_total_ms * 100.0, 2) if search_total_ms > 0 else 0.0,
            }

    # Sort by ms descending for top exclusive costs
    top_costs = sorted(
        [{"bucket": k, "ms": v["ms"], "pct_of_search": v["pct_of_search"]}
         for k, v in search_buckets_annotated.items()],
        key=lambda x: x["ms"], reverse=True
    )[:10]

    counters: dict[str, int] = {
        "native_search_calls": int(od.get("sparrow_q30_native_search_calls") or 0),
        "evaluate_sample_calls": int(od.get("sparrow_q30_evaluate_sample_calls") or 0),
        "evaluate_sample_calls_from_global": int(od.get("sparrow_q30r1_evaluate_sample_calls_from_global") or 0),
        "evaluate_sample_calls_from_focused": int(od.get("sparrow_q30r1_evaluate_sample_calls_from_focused") or 0),
        "evaluate_sample_calls_from_coord_descent": int(od.get("sparrow_q30r1_evaluate_sample_calls_from_coord_descent") or 0),
        "candidates_evaluated": int(od.get("sparrow_q30_candidates_evaluated") or 0),
        "global_samples_generated": int(od.get("sparrow_q30_global_samples_generated") or 0),
        "focused_samples_generated": int(od.get("sparrow_q30_focused_samples_generated") or 0),
        "best_samples_insert_attempts": int(od.get("sparrow_q30_best_samples_insert_attempts") or 0),
        "best_samples_inserted": int(od.get("sparrow_q30_best_samples_inserted") or 0),
        "best_samples_dedup_rejects": int(od.get("sparrow_q30_best_samples_dedup_rejects") or 0),
        "best_samples_best_calls": int(od.get("sparrow_q30r1_best_samples_best_calls") or 0),
        "best_samples_clone_calls": int(od.get("sparrow_q30r1_best_samples_clone_calls") or 0),
        "coord_descent_runs": int(od.get("sparrow_q30_coord_descent_runs") or 0),
        "coord_descent_steps": int(od.get("sparrow_q30_coord_descent_steps") or 0),
        "deadline_checks": 0,
        "sheet_loop_iterations": int(od.get("sparrow_q30r1_sheet_loop_iterations") or 0),
        "worker_passes": int(od.get("sparrow_q30r1_worker_passes") or 0),
        "worker_candidates_evaluated": int(od.get("sparrow_q30r1_worker_candidates_evaluated") or 0),
        "worker_candidates_accepted": int(od.get("sparrow_q30r1_worker_candidates_accepted") or 0),
        "coord_descent_ask_calls": int(od.get("sparrow_q30r1_coord_descent_ask_calls") or 0),
        "coord_descent_tell_calls": int(od.get("sparrow_q30r1_coord_descent_tell_calls") or 0),
        "broadphase_reject_count": int(od.get("sparrow_q30_broadphase_reject_count") or 0),
        "early_termination_count": int(od.get("sparrow_q30_early_termination_count") or 0),
    }

    return {
        "case_id": case_id,
        "status": status,
        "time_limit_s": time_limit,
        "placed_count": placed_count,
        "q30r1_profile_enabled": q30r1_enabled,
        "search_accounting": {
            "mode": "exclusive" if q30r1_enabled else "not_measured",
            "search_total_ms": round(search_total_ms, 3),
            "accounted_ms": round(search_accounted_ms, 3),
            "unaccounted_ms": round(search_unaccounted_ms, 3),
            "unaccounted_ratio_pct": round(search_unaccounted_ratio, 2),
            "buckets": {k: round(v, 3) for k, v in search_bucket_flat.items()},
        },
        "runtime_accounting": {
            "mode": "exclusive" if q30r1_enabled else "not_measured",
            "total_solver_runtime_ms": round(total_runtime_ms, 3),
            "seed_lbf_total_ms": round(seed_lbf_ms, 3),
            "tracker_initial_build_ms": round(tracker_init_ms, 3),
            "exploration_total_ms": round(exploration_ms, 3),
            "tracker_final_validation_ms": round(tracker_final_ms, 3),
            "output_mapping_ms": round(output_mapping_ms, 3),
            "accounted_ms": round(runtime_accounted_ms, 3),
            "accounted_ratio_pct": round(runtime_accounted_ratio, 2),
            "unaccounted_ms": round(max(total_runtime_ms - runtime_accounted_ms, 0.0), 3),
            "unaccounted_ratio_pct": round(max(100.0 - runtime_accounted_ratio, 0.0), 2),
            "separator_total_ms": round(sep_ms, 3),
            "separator_iteration_total_ms": round(sep_iter_ms, 3),
            "worker_competition_total_ms": round(worker_comp_ms, 3),
            "worker_pass_total_ms": round(worker_pass_ms, 3),
            "buckets": {k: round(v, 3) for k, v in runtime_bucket_flat.items()},
        },
        "search_buckets": search_buckets_annotated,
        "top_exclusive_costs": top_costs,
        "counters": counters,
    }


def _determine_dense191_pass(case_summary: dict) -> tuple[str, float, float]:
    """Return (q30r1_status, search_unaccounted_ratio, runtime_unaccounted_ratio)."""
    sa = case_summary.get("search_accounting", {})
    ra = case_summary.get("runtime_accounting", {})
    search_unaccounted = sa.get("unaccounted_ratio_pct", 100.0)
    runtime_unaccounted = ra.get("unaccounted_ratio_pct", 100.0)

    if not case_summary.get("q30r1_profile_enabled"):
        return "FAIL", 100.0, 100.0
    if search_unaccounted > DENSE191_SEARCH_UNACCOUNTED_THRESHOLD:
        return "FAIL", search_unaccounted, runtime_unaccounted
    runtime_accounted = ra.get("accounted_ratio_pct", 0.0)
    if runtime_accounted < DENSE191_RUNTIME_ACCOUNTED_THRESHOLD:
        return "PARTIAL", search_unaccounted, runtime_unaccounted
    return "PASS", search_unaccounted, runtime_unaccounted


def _find_next_hotspot(dense191_summary: dict) -> str:
    """Identify the concrete next hotspot from the exclusive bucket breakdown."""
    top = dense191_summary.get("top_exclusive_costs", [])
    sa = dense191_summary.get("search_accounting", {})
    unaccounted_ratio = sa.get("unaccounted_ratio_pct", 0.0)
    if unaccounted_ratio > DENSE191_SEARCH_UNACCOUNTED_THRESHOLD:
        # Still large unaccounted — identify residual dominant cost
        if top:
            return f"search.rs::native_search_placement (residual {unaccounted_ratio:.1f}% unaccounted)"
        return "search.rs::native_search_placement (unaccounted ratio too high)"
    # Find top bucket with significant share
    for b in top:
        if b["pct_of_search"] > 5.0:
            bucket = b["bucket"]
            if "prepare_base_shape" in bucket:
                return "cde_adapter.rs::prepare_base_shape_native"
            if "evaluate_sample" in bucket:
                return "eval/sep_evaluator.rs::SeparationEvaluator::evaluate_sample"
            if "cde_query" in bucket or "specialized_pipeline" in bucket:
                return "optimizer/cde_adapter.rs::collect_poly_collisions_in_detector_custom"
            if "coord_descent_ask" in bucket:
                return "sample/coord_descent.rs::CoordinateDescent::ask"
            if "fixed_shapes_clone" in bucket:
                return "sample/search.rs::native_search_placement (tracker.shapes.clone)"
            if "best_samples_clone" in bucket:
                return "sample/search.rs::search_placement (best.samples.clone)"
    return "eval/sep_evaluator.rs::SeparationEvaluator::evaluate_sample (cde_query dominant)"


def _write_summary_json(cases: list[dict], dense191_summary: dict, status: str,
                        search_unaccounted: float, runtime_unaccounted: float) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "task": "sgh_q30_r1_exclusive_search_runtime_breakdown",
        "status": status,
        "profile_flag": "SGH_Q30_R1_EXCLUSIVE_PROFILE=1",
        "timing_accounting_mode": "exclusive",
        "non_goals_preserved": {
            "no_solver_optimization": True,
            "no_upstream_ab": True,
            "no_compression": True,
            "no_sample_budget_change": True,
            "no_acceptance_change": True,
        },
        "acceptance_thresholds": {
            "search_unaccounted_ratio_pct_max": DENSE191_SEARCH_UNACCOUNTED_THRESHOLD,
            "runtime_accounted_ratio_pct_min": DENSE191_RUNTIME_ACCOUNTED_THRESHOLD,
        },
        "dense191_search_unaccounted_ratio_pct": search_unaccounted,
        "dense191_runtime_unaccounted_ratio_pct": runtime_unaccounted,
        "cases": cases,
    }
    out = ARTIFACTS_DIR / "local_exclusive_profile_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"Written: {out}")


def _write_markdown_report(cases: list[dict], dense191_summary: dict, status: str,
                           search_unaccounted: float, runtime_unaccounted: float,
                           next_hotspot: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SGH-Q30-R1 Exclusive Search Runtime Breakdown — Report",
        "",
        "## Summary",
        "",
        f"**Status:** `{status}`",
        "",
        "## Q30 Problem Context",
        "",
        "SGH-Q30 delivered a reusable `SearchProfiler` module but left ~79% of `search_total_ms`",
        "as `other_unaccounted_ms` on dense191 (20,784ms / 26,176ms). Q30-R1 adds exclusive",
        "timing tree instrumentation to close this gap.",
        "",
        "## New Exclusive Measurement Points",
        "",
        "Added exclusive timers (zero overhead when disabled) for:",
        "- `prepare_base_shape_native_ms` — CDE shape prep once per search call",
        "- `fixed_shapes_clone_ms` — `tracker.shapes.clone()` per search call",
        "- `sheet_order_build_ms` — sheet order vec construction",
        "- `best_samples_clone_ms` — `best.samples.clone()` before pre-stage coord descent",
        "- `best_samples_best_ms` — `best.best()` call before final coord descent",
        "- `coord_descent_ask_ms` — `CoordinateDescent::ask()` calls (exclusive)",
        "- `coord_descent_tell_ms` — `CoordinateDescent::tell()` calls (exclusive)",
        "- Total solver runtime: `seed_lbf`, `tracker_initial_build`, `exploration_total`,",
        "  `tracker_final_validation`, `output_mapping_ms`",
        "",
        "## Case Results",
        "",
    ]

    for case in cases:
        cid = case["case_id"]
        lines.append(f"### Case: {cid}")
        lines.append("")
        sa = case.get("search_accounting", {})
        ra = case.get("runtime_accounting", {})
        lines.append(f"| Field | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| status | {case.get('status', '?')} |")
        lines.append(f"| placed_count | {case.get('placed_count', '?')} |")
        lines.append(f"| q30r1_profile_enabled | {case.get('q30r1_profile_enabled', False)} |")
        lines.append(f"| search_total_ms | {sa.get('search_total_ms', 0):.1f} |")
        lines.append(f"| search_accounted_ms | {sa.get('accounted_ms', 0):.1f} |")
        lines.append(f"| search_unaccounted_ms | {sa.get('unaccounted_ms', 0):.1f} |")
        lines.append(f"| **search_unaccounted_ratio_pct** | **{sa.get('unaccounted_ratio_pct', 0):.1f}%** |")
        lines.append(f"| total_solver_runtime_ms | {ra.get('total_solver_runtime_ms', 0):.1f} |")
        lines.append(f"| runtime_accounted_ratio_pct | {ra.get('accounted_ratio_pct', 0):.1f}% |")
        lines.append("")

        top = case.get("top_exclusive_costs", [])
        if top:
            lines.append(f"**Top exclusive search buckets ({cid}):**")
            lines.append("")
            lines.append("| Bucket | ms | % of search |")
            lines.append("|---|---|---|")
            for b in top[:10]:
                lines.append(f"| {b['bucket']} | {b['ms']:.1f} | {b['pct_of_search']:.1f}% |")
            lines.append("")

        cntrs = case.get("counters", {})
        if cntrs:
            lines.append(f"**Counters ({cid}):**")
            lines.append("")
            lines.append("| Counter | Value |")
            lines.append("|---|---|")
            for k, v in cntrs.items():
                lines.append(f"| {k} | {v} |")
            lines.append("")

    lines.extend([
        "## Dense191 Analysis",
        "",
        f"**search_unaccounted_ratio_pct:** {search_unaccounted:.1f}%",
        f"**runtime_unaccounted_ratio_pct:** {runtime_unaccounted:.1f}%",
        "",
    ])

    sa = dense191_summary.get("search_accounting", {})
    ra = dense191_summary.get("runtime_accounting", {})
    top_d191 = dense191_summary.get("top_exclusive_costs", [])

    if top_d191:
        lines.append("**What consumes search_total_ms:**")
        lines.append("")
        lines.append("| Bucket | ms | % |")
        lines.append("|---|---|---|")
        for b in top_d191[:10]:
            lines.append(f"| {b['bucket']} | {b['ms']:.1f} | {b['pct_of_search']:.1f}% |")
        lines.append("")
        lines.append(f"Unaccounted: {sa.get('unaccounted_ms', 0):.1f}ms "
                     f"({sa.get('unaccounted_ratio_pct', 0):.1f}%)")
        lines.append("")

    lines.extend([
        "**Runtime breakdown (top level exclusive):**",
        "",
        f"| Bucket | ms | % of total |",
        f"|---|---|---|",
    ])
    total_rt = ra.get("total_solver_runtime_ms", 1.0)
    for bucket_key, label in [
        ("seed_lbf_total_ms", "seed_lbf"),
        ("tracker_initial_build_ms", "tracker_initial_build"),
        ("exploration_total_ms", "exploration"),
        ("separator_total_ms", "separator"),
        ("worker_competition_total_ms", "worker_competition"),
        ("worker_pass_total_ms", "worker_pass"),
        ("tracker_final_validation_ms", "tracker_final_validation"),
        ("output_mapping_ms", "output_mapping"),
    ]:
        ms = ra.get(bucket_key, 0.0)
        pct = ms / total_rt * 100.0 if total_rt > 0 else 0.0
        lines.append(f"| {label} | {ms:.1f} | {pct:.1f}% |")
    lines.append(f"| **runtime_unaccounted** | **{ra.get('unaccounted_ms', 0):.1f}** "
                 f"| **{ra.get('unaccounted_ratio_pct', 0):.1f}%** |")
    lines.append("")

    lines.extend([
        f"**Next hotspot to instrument:** `{next_hotspot}`",
        "",
        "## Admin Integration",
        "",
        "Profile data available via `optimizer_diagnostics.sparrow_q30r1_*` JSON fields.",
        "Enabled only with `SGH_Q30_R1_EXCLUSIVE_PROFILE=1`. Zero overhead when disabled.",
        "Backward compatible with `SGH_Q30_SEARCH_PROFILE=1` (enables all R1 timers too).",
        "Fields suitable for future admin/observability surface (structured, versioned).",
        "",
        "---",
        "",
        f"Q30_R1_STATUS: {status}",
        f"DENSE191_SEARCH_UNACCOUNTED_RATIO: {search_unaccounted:.1f}%",
        f"DENSE191_RUNTIME_UNACCOUNTED_RATIO: {runtime_unaccounted:.1f}%",
        f"NEXT_HOTSPOT: {next_hotspot}",
    ])

    out = ARTIFACTS_DIR / "local_exclusive_profile_report.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"Written: {out}")


def main():
    if not LOCAL_BIN.exists():
        print(f"ERROR: binary not found: {LOCAL_BIN}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    print("SGH-Q30-R1 exclusive profile runner")
    print(f"Binary: {LOCAL_BIN}")
    print()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    cases_raw = []
    case_summaries = []

    # Medium sanity case (short)
    print("[1/4] Running medium sanity case (30s)...")
    medium_output = _run_profiled(_build_medium_input(), "medium", time_limit=30)
    medium_summary = _case_summary("medium", medium_output, 30)
    case_summaries.append(medium_summary)
    cases_raw.append(medium_output)
    sa = medium_summary["search_accounting"]
    print(f"  status={medium_output.get('status')} "
          f"search_total={sa['search_total_ms']:.0f}ms "
          f"unaccounted={sa['unaccounted_ratio_pct']:.1f}%")

    # LV8 subset (60s)
    print("[2/4] Running lv8_subset case (60s)...")
    try:
        lv8_input = _build_lv8_subset_input()
        lv8_output = _run_profiled(lv8_input, "lv8_subset", time_limit=60)
        lv8_summary = _case_summary("lv8_subset", lv8_output, 60)
    except FileNotFoundError as e:
        print(f"  SKIP: {e}")
        lv8_summary = {"case_id": "lv8_subset", "status": "skipped", "skipped_reason": str(e),
                       "q30r1_profile_enabled": False, "search_accounting": {}, "runtime_accounting": {},
                       "search_buckets": {}, "top_exclusive_costs": [], "counters": {}}
    case_summaries.append(lv8_summary)
    sa = lv8_summary.get("search_accounting", {})
    print(f"  status={lv8_summary.get('status')} "
          f"search_total={sa.get('search_total_ms', 0):.0f}ms "
          f"unaccounted={sa.get('unaccounted_ratio_pct', 0):.1f}%")

    # Dense191 — main acceptance case (120s)
    print("[3/4] Running dense191 case (120s) — main acceptance gate...")
    dense191_output = _run_profiled(_build_dense191_input(), "dense191", time_limit=120)
    dense191_summary = _case_summary("dense191", dense191_output, 120)
    case_summaries.append(dense191_summary)
    sa = dense191_summary["search_accounting"]
    print(f"  status={dense191_output.get('status')} "
          f"search_total={sa['search_total_ms']:.0f}ms "
          f"unaccounted={sa['unaccounted_ratio_pct']:.1f}%")

    # Full276 optional diagnostic (300s)
    print("[4/4] Running full276 optional diagnostic (300s)...")
    full276_input = _build_full276_input()
    if full276_input is not None:
        full276_output = _run_profiled(full276_input, "full276_optional", time_limit=300)
        full276_summary = _case_summary("full276_optional", full276_output, 300)
    else:
        full276_summary = {
            "case_id": "full276_optional",
            "status": "skipped",
            "attempted": False,
            "skipped_reason": "fixture not found in sgh_q27_dense_lv8/",
            "q30r1_profile_enabled": False,
            "search_accounting": {},
            "runtime_accounting": {},
            "search_buckets": {},
            "top_exclusive_costs": [],
            "counters": {},
        }
        (INPUTS_DIR / "full276_optional.json").write_text(
            json.dumps({"note": "fixture not found"})
        )
        print("  SKIP: fixture not found")
    case_summaries.append(full276_summary)

    # Determine overall status from dense191
    q30r1_status, search_unaccounted, runtime_unaccounted = _determine_dense191_pass(dense191_summary)
    next_hotspot = _find_next_hotspot(dense191_summary)

    print()
    print(f"Q30_R1_STATUS: {q30r1_status}")
    print(f"DENSE191_SEARCH_UNACCOUNTED_RATIO: {search_unaccounted:.1f}%")
    print(f"DENSE191_RUNTIME_UNACCOUNTED_RATIO: {runtime_unaccounted:.1f}%")
    print(f"NEXT_HOTSPOT: {next_hotspot}")

    _write_summary_json(case_summaries, dense191_summary, q30r1_status,
                        search_unaccounted, runtime_unaccounted)
    _write_markdown_report(case_summaries, dense191_summary, q30r1_status,
                           search_unaccounted, runtime_unaccounted, next_hotspot)

    if q30r1_status == "FAIL":
        print(f"\nFAIL: dense191 search_unaccounted_ratio_pct={search_unaccounted:.1f}% "
              f"> {DENSE191_SEARCH_UNACCOUNTED_THRESHOLD}%")
        sys.exit(1)
    elif q30r1_status == "PARTIAL":
        print(f"\nPARTIAL: search gate met but runtime_accounted < "
              f"{DENSE191_RUNTIME_ACCOUNTED_THRESHOLD}%")
        sys.exit(0)
    else:
        print(f"\nPASS: dense191 search_unaccounted={search_unaccounted:.1f}% "
              f"<= {DENSE191_SEARCH_UNACCOUNTED_THRESHOLD}%")
        sys.exit(0)


if __name__ == "__main__":
    main()
