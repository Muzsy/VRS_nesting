#!/usr/bin/env python3
"""SGH-Q29 smoke validator.

This script validates Q29 measurement artifacts. It does not run the benchmark
itself; it verifies that the upstream A/B summary and local CDE hotspot profiler
summary are present, structurally valid, and do not mislabel a local vrs_solver
reference build as upstream Sparrow.

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
ART = ROOT / "artifacts" / "benchmarks" / "sgh_q29"
UPSTREAM_SUMMARY = ART / "upstream_ab_summary.json"
LOCAL_SUMMARY = ART / "local_cde_hotspot_summary.json"
UPSTREAM_REPORT = ART / "upstream_ab_report.md"
LOCAL_REPORT = ART / "local_cde_hotspot_report.md"

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


def validate_upstream_summary() -> None:
    print("\n=== Phase A: upstream A/B summary ===")
    check(UPSTREAM_SUMMARY.exists(), f"exists: {UPSTREAM_SUMMARY}")
    check(UPSTREAM_REPORT.exists(), f"exists: {UPSTREAM_REPORT}")
    if not UPSTREAM_SUMMARY.exists():
        return
    data = load_json(UPSTREAM_SUMMARY)
    status = str(data.get("status", ""))
    check(status in {"PASS", "BLOCKED", "FAIL"}, f"valid upstream status: {status!r}")
    up = data.get("upstream_sparrow") or {}
    cases = data.get("cases") or []

    if status == "PASS":
        commit = str(up.get("commit") or "")
        entry = str(up.get("binary_or_entrypoint") or "")
        source = str(up.get("source_path") or "")
        check(bool(commit) and commit not in {"unknown", "local"}, "upstream commit recorded")
        check(".cache/sparrow" in source or "sparrow" in source.lower(), "upstream source path recorded")
        check(bool(entry), "upstream binary_or_entrypoint recorded")
        lowered = entry.lower()
        check("vrs_solver" not in lowered, "upstream entrypoint is not local vrs_solver")
        check("no-session" not in lowered and "reference" not in lowered, "upstream entrypoint is not local no-session/reference")
        check(len(cases) >= 2, f"at least 2 upstream A/B cases, got {len(cases)}")
        for i, case in enumerate(cases):
            check("upstream" in case and "local" in case, f"case {i} has upstream+local blocks")
            check(str(case.get("case_id") or ""), f"case {i} has case_id")
            runtime = (case.get("upstream") or {}).get("runtime_ms")
            check(isinstance(runtime, (int, float)) and runtime >= 0, f"case {i} upstream runtime_ms present")
    elif status == "BLOCKED":
        reason = str(data.get("blocked_reason") or data.get("reason") or "")
        check(bool(reason), "BLOCKED has explicit reason")
        print("  [INFO] Phase A BLOCKED; no upstream runtime claim should be made.")
    else:
        print("  [INFO] Phase A status is FAIL; inspect upstream_ab_report.md")


def validate_local_summary() -> None:
    print("\n=== Phase B: local CDE hotspot summary ===")
    check(LOCAL_SUMMARY.exists(), f"exists: {LOCAL_SUMMARY}")
    check(LOCAL_REPORT.exists(), f"exists: {LOCAL_REPORT}")
    if not LOCAL_SUMMARY.exists():
        return
    data = load_json(LOCAL_SUMMARY)
    status = str(data.get("status", ""))
    check(status in {"PASS", "FAIL"}, f"valid local profiler status: {status!r}")
    check(str(data.get("profile_flag") or ""), "profile_flag recorded")
    cases = data.get("cases") or []
    check(len(cases) >= 2, f"at least 2 local profiler cases, got {len(cases)}")

    required = [
        "native_search_calls",
        "candidates_evaluated",
        "session_build_ms",
        "deregister_reregister_ms",
        "candidate_transform_prepare_ms",
        "cde_query_collect_ms",
        "specialized_pipeline_ms",
        "hazard_loss_ms",
        "boundary_check_ms",
        "broadphase_reject_count",
        "early_termination_count",
    ]
    for i, case in enumerate(cases):
        check(str(case.get("case_id") or ""), f"case {i} has case_id")
        check(isinstance(case.get("runtime_ms"), (int, float)), f"case {i} runtime_ms present")
        profile = case.get("profile") or {}
        for key in required:
            check(key in profile, f"case {i} profile has {key}")
        top = case.get("top_costs_percent") or []
        check(isinstance(top, list) and len(top) > 0, f"case {i} has top_costs_percent")


def main() -> int:
    print("=== SGH-Q29 smoke validator ===")
    validate_upstream_summary()
    validate_local_summary()
    print()
    if FAIL:
        print(f"FAIL — {FAIL} check(s) failed, {PASS} passed")
        return 2
    print(f"PASS — {PASS} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
