#!/usr/bin/env python3
"""SGH-Q30-R1 smoke validator — exclusive search runtime breakdown.

This script validates Q30-R1 artifacts. It does not run the solver.
It is intentionally strict: Q30-R1 may not pass if dense191 still has a large
unaccounted search-time block or if the output is nested/alias timing disguised
as exclusive accounting.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts" / "benchmarks" / "sgh_q30_r1" / "local_exclusive_profile_summary.json"
REPORT = ROOT / "artifacts" / "benchmarks" / "sgh_q30_r1" / "local_exclusive_profile_report.md"
CODEX_REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q30_r1_exclusive_search_runtime_breakdown.md"
PROFILE_RS = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow" / "profile.rs"

REQUIRED_CASES = {"medium", "lv8_subset", "dense191"}

REQUIRED_SEARCH_BUCKETS = [
    "native_search_setup_ms",
    "prepare_base_shape_native_ms",
    "fixed_shapes_clone_ms",
    "sheet_order_build_ms",
    "sheet_loop_total_ms",
    "sheet_loop_overhead_ms",
    "global_loop_total_ms",
    "focused_loop_total_ms",
    "sample_generation_ms",
    "sample_acceptance_loop_ms",
    "best_samples_insert_dedup_ms",
    "best_samples_best_ms",
    "best_samples_clone_ms",
    "coord_descent_total_ms",
    "coord_descent_eval_ms",
    "coord_descent_ask_ms",
    "coord_descent_tell_ms",
    "coord_descent_overhead_ms",
    "evaluate_sample_total_ms",
    "evaluate_sample_exclusive_overhead_ms",
    "evaluator_orchestration_ms",
    "candidate_transform_prepare_ms",
    "cde_query_collect_ms",
    "specialized_pipeline_ms",
    "hazard_loss_ms",
    "boundary_check_ms",
    "broadphase_reject_ms",
    "session_build_ms",
    "deregister_reregister_ms",
    "deadline_check_ms",
    "rng_shuffle_ms",
    "rng_sample_generation_ms",
]

REQUIRED_RUNTIME_BUCKETS = [
    "adapter_solve_total_ms",
    "sparrow_optimizer_solve_total_ms",
    "seed_lbf_total_ms",
    "separator_total_ms",
    "separator_iteration_total_ms",
    "worker_competition_total_ms",
    "worker_pass_total_ms",
    "tracker_initial_build_ms",
    "tracker_final_validation_ms",
    "output_mapping_ms",
]

REQUIRED_COUNTERS = [
    "native_search_calls",
    "evaluate_sample_calls",
    "evaluate_sample_calls_from_global",
    "evaluate_sample_calls_from_focused",
    "evaluate_sample_calls_from_coord_descent",
    "candidates_evaluated",
    "global_samples_generated",
    "focused_samples_generated",
    "best_samples_insert_attempts",
    "best_samples_inserted",
    "best_samples_dedup_rejects",
    "best_samples_best_calls",
    "best_samples_clone_calls",
    "coord_descent_runs",
    "coord_descent_steps",
    "deadline_checks",
    "sheet_loop_iterations",
    "worker_passes",
    "worker_candidates_evaluated",
    "worker_candidates_accepted",
]

pass_count = 0
fail_count = 0


def check(cond: bool, msg: str) -> None:
    global pass_count, fail_count
    if cond:
        pass_count += 1
        print(f"[PASS] {msg}")
    else:
        fail_count += 1
        print(f"[FAIL] {msg}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        check(False, f"missing JSON: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        check(False, f"invalid JSON {path}: {exc}")
        return {}


def find_case(summary: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in summary.get("cases", []):
        if case.get("case_id") == case_id:
            return case
    return {}


def get_accounting(case: dict[str, Any], key: str) -> dict[str, Any]:
    # Canonical Q30-R1 schema.
    if isinstance(case.get(key), dict):
        return case[key]
    # Backward-compatible fallback for accidental flat export; still validated strictly.
    return {}


def numeric(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    summary = load_json(SUMMARY)
    report_text = REPORT.read_text(encoding="utf-8", errors="replace") if REPORT.exists() else ""
    codex_report_text = CODEX_REPORT.read_text(encoding="utf-8", errors="replace") if CODEX_REPORT.exists() else ""
    profile_text = PROFILE_RS.read_text(encoding="utf-8", errors="replace") if PROFILE_RS.exists() else ""

    check(bool(summary), "summary JSON is present and parseable")
    check(REPORT.exists(), "markdown profile report exists")
    check(CODEX_REPORT.exists(), "Codex report exists")
    check(PROFILE_RS.exists(), "profile.rs exists")

    check(summary.get("task") == "sgh_q30_r1_exclusive_search_runtime_breakdown", "summary task slug matches Q30-R1")
    check(summary.get("timing_accounting_mode") == "exclusive", "summary timing_accounting_mode == exclusive")

    cases = {c.get("case_id") for c in summary.get("cases", []) if isinstance(c, dict)}
    for c in REQUIRED_CASES:
        check(c in cases, f"required case present: {c}")

    dense = find_case(summary, "dense191")
    check(bool(dense), "dense191 case present")

    search_acc = get_accounting(dense, "search_accounting")
    runtime_acc = get_accounting(dense, "runtime_accounting")
    counters = dense.get("counters") or dense.get("profile", {})

    check(search_acc.get("mode") == "exclusive", "dense191 search accounting mode is exclusive")
    check(runtime_acc.get("mode") == "exclusive", "dense191 runtime accounting mode is exclusive")

    search_total = numeric(search_acc.get("search_total_ms"))
    search_accounted = numeric(search_acc.get("accounted_ms"))
    search_unacc_ratio = numeric(search_acc.get("unaccounted_ratio_pct"), 999.0)
    runtime_total = numeric(runtime_acc.get("total_solver_runtime_ms"))
    runtime_accounted = numeric(runtime_acc.get("accounted_ms"))
    runtime_unacc_ratio = numeric(runtime_acc.get("unaccounted_ratio_pct"), 999.0)

    check(search_total > 0, f"dense191 search_total_ms > 0 ({search_total})")
    check(search_accounted >= search_total * 0.85, f"dense191 search accounted >=85% ({search_accounted}/{search_total})")
    check(search_accounted <= search_total * 1.10, f"dense191 search accounted <=110% ({search_accounted}/{search_total})")
    check(search_unacc_ratio <= 15.0, f"dense191 search unaccounted <=15% ({search_unacc_ratio}%)")
    check(runtime_total > 0, f"dense191 total_solver_runtime_ms > 0 ({runtime_total})")
    check(runtime_accounted >= runtime_total * 0.75, f"dense191 runtime accounted >=75% ({runtime_accounted}/{runtime_total})")

    buckets = search_acc.get("buckets") or {}
    for b in REQUIRED_SEARCH_BUCKETS:
        check(b in buckets, f"search bucket present: {b}")
        if b in buckets:
            val = buckets[b]
            check(isinstance(val, (int, float)) and float(val) >= 0.0, f"search bucket numeric non-negative: {b}")

    runtime_buckets = runtime_acc.get("buckets") or {}
    for b in REQUIRED_RUNTIME_BUCKETS:
        check(b in runtime_buckets, f"runtime bucket present: {b}")
        if b in runtime_buckets:
            val = runtime_buckets[b]
            check(isinstance(val, (int, float)) and float(val) >= 0.0, f"runtime bucket numeric non-negative: {b}")

    for c in REQUIRED_COUNTERS:
        check(c in counters, f"counter present: {c}")
        if c in counters:
            check(isinstance(counters[c], int) and counters[c] >= 0, f"counter integer non-negative: {c}")

    # Explicit anti-evasion checks.
    sg = numeric(buckets.get("sample_generation_ms"), -1.0)
    rng_sample = numeric(buckets.get("rng_sample_generation_ms"), -1.0)
    rng_shuffle = numeric(buckets.get("rng_shuffle_ms"), -1.0)
    old_alias = dense.get("profile", {}).get("rng_shuffle_sample_loop_ms")
    check("rng_shuffle_sample_loop_ms" not in buckets, "old alias bucket rng_shuffle_sample_loop_ms not used as Q30-R1 proof")
    check(not (old_alias is not None and numeric(old_alias) == sg and rng_sample < 0), "old Q30 alias timing not reused")
    check(rng_sample >= 0.0 and rng_shuffle >= 0.0, "rng sample and rng shuffle are separate fields")

    # profile.rs should have real finalization and exclusive concepts.
    check("finalize" in profile_text.lower(), "profile.rs contains finalize/equivalent finalization")
    check("exclusive" in profile_text.lower(), "profile.rs contains explicit exclusive accounting language/API")
    check("SGH_Q30_R1_EXCLUSIVE_PROFILE" in profile_text or "SGH_Q30_SEARCH_PROFILE" in profile_text, "profile flag is present")

    # Report markers must exist and not claim PASS if hard gates fail.
    combined_report = report_text + "\n" + codex_report_text
    check("Q30_R1_STATUS:" in combined_report, "report contains Q30_R1_STATUS marker")
    check("DENSE191_SEARCH_UNACCOUNTED_RATIO:" in combined_report, "report contains dense search unaccounted marker")
    check("DENSE191_RUNTIME_UNACCOUNTED_RATIO:" in combined_report, "report contains dense runtime unaccounted marker")
    hotspot_match = re.search(r"NEXT_HOTSPOT:\s*(\S+::\S+)", combined_report)
    check(bool(hotspot_match), "report contains concrete NEXT_HOTSPOT path::function")

    hard_gate_ok = search_unacc_ratio <= 15.0 and runtime_accounted >= runtime_total * 0.75
    if not hard_gate_ok:
        check("Q30_R1_STATUS: PASS" not in combined_report, "report must not claim PASS when hard gates fail")

    # Non-goal preservation should be stated in summary.
    non_goals = summary.get("non_goals_preserved") or {}
    for k in ["no_solver_optimization", "no_upstream_ab", "no_compression", "no_sample_budget_change", "no_acceptance_change"]:
        check(non_goals.get(k) is True, f"non-goal preserved: {k}")

    print(f"\nPASS={pass_count} FAIL={fail_count}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
