#!/usr/bin/env python3
"""SGH-Q30 smoke validator.

Validates local search/CDE profiler artifacts. This script does not run the
benchmark; it checks that Q30 produced the required reusable profiling summary
and reports the new search-loop cost breakdown fields.

Exit codes:
  0 PASS
  2 FAIL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "benchmarks" / "sgh_q30"
SUMMARY = ART / "local_search_profile_summary.json"
REPORT = ART / "local_search_profile_report.md"

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


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        check(False, f"read/parse JSON failed: {path}: {exc}")
        return {}


REQUIRED_PROFILE_FIELDS = [
    "native_search_calls",
    "candidates_evaluated",
    "evaluate_sample_calls",
    "global_samples_generated",
    "focused_samples_generated",
    "coord_descent_runs",
    "coord_descent_steps",
    "best_samples_insert_attempts",
    "best_samples_inserted",
    "best_samples_dedup_rejects",
    "rng_shuffle_or_sample_loop_count",
    "early_termination_count",
    "broadphase_reject_count",
    "search_total_ms",
    "sample_generation_ms",
    "best_samples_insert_dedup_ms",
    "coord_descent_total_ms",
    "evaluate_sample_total_ms",
    "evaluator_orchestration_ms",
    "rng_shuffle_sample_loop_ms",
    "candidate_transform_prepare_ms",
    "cde_query_collect_ms",
    "specialized_pipeline_ms",
    "hazard_loss_ms",
    "boundary_check_ms",
    "session_build_ms",
    "deregister_reregister_ms",
    "other_unaccounted_ms",
    "per_candidate_avg_ms",
    "per_evaluate_sample_avg_ms",
    "per_search_avg_ms",
]

CORE_NEW_FIELDS = [
    "sample_generation_ms",
    "best_samples_insert_dedup_ms",
    "coord_descent_total_ms",
    "evaluate_sample_calls",
    "evaluate_sample_total_ms",
    "evaluator_orchestration_ms",
    "rng_shuffle_sample_loop_ms",
    "per_candidate_avg_ms",
]


def is_number_or_na(value: Any) -> bool:
    return isinstance(value, (int, float)) or value == "not_available"


def validate_summary() -> None:
    print("=== SGH-Q30 local search profiler artifact smoke ===")
    check(SUMMARY.exists(), f"exists: {SUMMARY}")
    check(REPORT.exists(), f"exists: {REPORT}")
    if not SUMMARY.exists():
        return

    data = load_json(SUMMARY)
    check(data.get("task") == "sgh_q30_local_sparrow_search_profiler_module", "task slug matches")
    check(data.get("status") in {"PASS", "FAIL"}, f"valid status: {data.get('status')!r}")
    check(str(data.get("profile_flag") or ""), "profile_flag recorded")
    check(
        data.get("timing_accounting_mode") in {"exclusive", "nested_with_notes", "mixed_with_notes"},
        f"valid timing_accounting_mode: {data.get('timing_accounting_mode')!r}",
    )

    module = data.get("module") or {}
    check(str(module.get("rust_path") or "").endswith(".rs"), "module.rust_path recorded")
    check(str(module.get("enabled_by") or ""), "module.enabled_by recorded")
    check(str(module.get("future_admin_integration_notes") or ""), "future admin integration notes recorded")

    cases = data.get("cases") or []
    check(isinstance(cases, list) and len(cases) >= 3, f"at least 3 cases, got {len(cases)}")
    case_ids = {str(c.get("case_id") or "") for c in cases}
    check("medium" in case_ids, "medium case present")
    check("lv8_subset" in case_ids, "lv8_subset case present")
    check("dense191" in case_ids or any(c.get("skipped_reason") for c in cases if c.get("case_id") == "dense191"), "dense191 present or skipped_reason recorded")

    for idx, case in enumerate(cases):
        cid = str(case.get("case_id") or f"case_{idx}")
        print(f"\n--- case {idx}: {cid} ---")
        check(str(case.get("input_path") or ""), f"{cid}: input_path recorded")
        check(case.get("status") in {"ok", "partial", "unsupported", "error", "skipped"}, f"{cid}: valid status")
        if case.get("status") == "skipped":
            check(str(case.get("skipped_reason") or ""), f"{cid}: skipped_reason recorded")
            continue
        check(isinstance(case.get("runtime_ms"), (int, float)), f"{cid}: runtime_ms numeric")
        profile = case.get("profile") or {}
        for key in REQUIRED_PROFILE_FIELDS:
            check(key in profile, f"{cid}: profile has {key}")
            if key in profile:
                check(is_number_or_na(profile[key]), f"{cid}: {key} numeric or not_available")
        for key in CORE_NEW_FIELDS:
            check(key in profile, f"{cid}: core new Q30 field present: {key}")
        search_total = float((profile or {}).get("search_total_ms") or 0.0)
        top = case.get("top_costs_percent") or []
        if search_total > 0:
            check(isinstance(top, list) and len(top) > 0, f"{cid}: top_costs_percent present (search active)")
        else:
            check(isinstance(top, list), f"{cid}: top_costs_percent is list (no search calls — constructive seed)")
        if top:
            first = top[0]
            check("name" in first and "percent_of_search_total" in first, f"{cid}: top cost has name+percent")
        notes = case.get("notes")
        check(isinstance(notes, list), f"{cid}: notes list present")

    if REPORT.exists():
        text = REPORT.read_text(encoding="utf-8", errors="replace")
        for needle in [
            "Final answer",
            "medium",
            "LV8",
            "dense191",
            "other_unaccounted",
            "admin",
        ]:
            check(needle.lower() in text.lower(), f"report mentions {needle}")


def main() -> int:
    validate_summary()
    print()
    if FAIL:
        print(f"FAIL — {FAIL} check(s) failed, {PASS} passed")
        return 2
    print(f"PASS — {PASS} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
