#!/usr/bin/env python3
"""SGH-Q31 smoke — CDE base-shape cache hot-path speedup validator.

Validates both static code invariants and Q31 runtime artifacts.

Exit codes:
  0 PASS
  2 FAIL
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts" / "benchmarks" / "sgh_q31" / "base_shape_cache_summary.json"
REPORT = ROOT / "artifacts" / "benchmarks" / "sgh_q31" / "base_shape_cache_report.md"
CODE_REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q31_cde_base_shape_cache_hotpath_speedup.md"

BASELINE_PREPARE_MS = 21433.1
MAX_HOTPATH_MS = BASELINE_PREPARE_MS * 0.10
MAX_FINAL_PAIRS = 88

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
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_comments(text: str) -> str:
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    return text


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def all_dicts(x: Any) -> Iterable[dict[str, Any]]:
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from all_dicts(v)
    elif isinstance(x, list):
        for v in x:
            yield from all_dicts(v)


def find_dense191(summary: Any) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for d in all_dicts(summary):
        joined = " ".join(str(d.get(k, "")) for k in ("case", "name", "fixture", "scenario", "label", "project_name", "id"))
        if "dense191" in joined.lower() or "dense_191" in joined.lower():
            candidates.append(d)
    # Prefer the richest dict with core metrics.
    if candidates:
        return max(candidates, key=lambda d: len(d.keys()))
    # Fallback: the only dict with exactly/at least 191 instances/placements.
    for d in all_dicts(summary):
        vals = [d.get(k) for k in ("instance_count", "requested_instances", "total_instances", "placed_count", "placed")]
        if any(v == 191 for v in vals):
            return d
    return None


def deep_get(d: dict[str, Any], names: list[str]) -> Any:
    # Direct keys first.
    for name in names:
        if name in d:
            return d[name]
    # Common nested buckets.
    for bucket in ("metrics", "optimizer_diagnostics", "diagnostics", "q30_profile", "q31_profile", "profile", "search_profile"):
        child = d.get(bucket)
        if isinstance(child, dict):
            for name in names:
                if name in child:
                    return child[name]
    # Recursive fallback.
    for sub in all_dicts(d):
        for name in names:
            if name in sub:
                return sub[name]
    return None


def as_float(v: Any, default: float | None = None) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().rstrip("%"))
        except ValueError:
            return default
    return default


def as_int(v: Any, default: int | None = None) -> int | None:
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v.strip().rstrip("%")))
        except ValueError:
            return default
    return default


def main() -> int:
    print("=== SGH-Q31 CDE base-shape cache hot-path speedup smoke ===")

    model_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/model.rs"))
    search_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/sample/search.rs"))
    lbf_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/lbf.rs"))
    tracker_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs"))
    profile_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/sparrow/profile.rs"))
    cde_adapter_rs = strip_comments(read(ROOT / "rust/vrs_solver/src/optimizer/cde_adapter.rs"))

    print("\n--- Static code invariants ---")
    check("base_shape" in model_rs and "Rc<CdeBaseShape>" in model_rs, "SPInstance/model stores Rc<CdeBaseShape>")
    check("HashMap" in model_rs and "prepare_base_shape_native" in model_rs, "SparrowProblem builds a base-shape cache")
    check("base_shape_cache" in model_rs or "base_shapes" in model_rs, "model has explicit base-shape cache variable")
    check("prepare_base_shape_native(&inst.part)" not in search_rs, "sample/search.rs no direct prepare_base_shape_native(&inst.part)")
    check("prepare_base_shape_native(&inst.part)" not in lbf_rs, "lbf.rs no direct prepare_base_shape_native(&inst.part)")
    check("prepare_shape_native(&inst.part" not in tracker_rs, "tracker no routine prepare_shape_native(&inst.part, ...) hot-path")
    check("transform_base_to_candidate" in search_rs and "base_shape" in search_rs, "search uses cached base_shape + transform_base_to_candidate")
    check("transform_base_to_candidate" in lbf_rs and "base_shape" in lbf_rs, "LBF uses cached base_shape + transform_base_to_candidate")
    check("transform_base_to_candidate" in tracker_rs and "base_shape" in tracker_rs, "tracker uses cached base_shape + transform_base_to_candidate")
    check("struct CdeBaseShape" in cde_adapter_rs, "CdeBaseShape still exists as reusable base geometry")

    required_profile_tokens = [
        "base_shape_cache_build_ms",
        "base_shape_cache_hits",
        "base_shape_cache_misses",
        "base_shape_cache_unique_parts",
        "base_shape_cache_reused_instances",
        "prepare_base_shape_native_hotpath_calls",
        "prepare_base_shape_native_hotpath_ms",
    ]
    for token in required_profile_tokens:
        check(token in profile_rs or token in model_rs, f"profiler/model exposes {token}")

    print("\n--- Artifact existence ---")
    check(SUMMARY.exists(), f"summary artifact exists: {SUMMARY.relative_to(ROOT)}")
    check(REPORT.exists(), f"benchmark report exists: {REPORT.relative_to(ROOT)}")
    check((ROOT / "artifacts/benchmarks/sgh_q31/inputs/dense191.json").exists(), "dense191 input artifact exists")
    check((ROOT / "artifacts/benchmarks/sgh_q31/inputs/lv8_subset.json").exists(), "lv8_subset input artifact exists")

    if SUMMARY.exists():
        print("\n--- Dense191 acceptance ---")
        summary = load_json(SUMMARY)
        dense = find_dense191(summary)
        check(dense is not None, "dense191 case found in summary")
        if dense is not None:
            status = deep_get(dense, ["status"])
            placed = as_int(deep_get(dense, ["placed_count", "placed", "placements_count"]))
            final_pairs = as_int(deep_get(dense, ["final_pairs", "sparrow_collision_graph_final_pairs", "collision_graph_final_pairs"]))
            hot_calls = as_int(deep_get(dense, ["prepare_base_shape_native_hotpath_calls", "base_shape_hotpath_calls", "q31_prepare_base_hotpath_calls"]))
            hot_ms = as_float(deep_get(dense, ["prepare_base_shape_native_hotpath_ms", "base_shape_hotpath_ms", "q31_prepare_base_hotpath_ms"]))
            misses = as_int(deep_get(dense, ["base_shape_cache_misses", "q31_base_shape_cache_misses"]))
            hits = as_int(deep_get(dense, ["base_shape_cache_hits", "q31_base_shape_cache_hits"]))
            unique_parts = as_int(deep_get(dense, ["base_shape_cache_unique_parts", "unique_part_count", "part_type_count", "part_types"]))
            instance_count = as_int(deep_get(dense, ["instance_count", "requested_instances", "total_instances", "selected_instance_count"])) or 191

            print(f"  [INFO] dense191 status={status} placed={placed} final_pairs={final_pairs} hot_calls={hot_calls} hot_ms={hot_ms} hits={hits} misses={misses} unique_parts={unique_parts} instances={instance_count}")

            check(status in {"partial", "ok"}, f"dense191 status partial/ok, got {status!r}")
            check(placed == 191, f"dense191 placed_count == 191, got {placed}")
            check(final_pairs is not None and final_pairs <= MAX_FINAL_PAIRS, f"dense191 final_pairs <= {MAX_FINAL_PAIRS}, got {final_pairs}")
            check(hot_calls == 0, f"hot-path prepare_base_shape_native calls == 0, got {hot_calls}")
            check(hot_ms is not None and hot_ms <= MAX_HOTPATH_MS, f"hot-path prepare ms <= {MAX_HOTPATH_MS:.2f}, got {hot_ms}")
            check(unique_parts is not None and unique_parts > 0, f"unique part count recorded, got {unique_parts}")
            if unique_parts is not None:
                check(misses is not None and misses <= unique_parts + 2, f"cache misses <= unique_parts + 2 ({unique_parts + 2}), got {misses}")
                check(hits is not None and hits >= instance_count - unique_parts, f"cache hits >= instances - unique_parts ({instance_count - unique_parts}), got {hits}")

    print("\n--- Final report markers ---")
    code_report = read(CODE_REPORT)
    for marker in [
        "Q31_STATUS:",
        "DENSE191_BASE_SHAPE_HOTPATH_CALLS:",
        "DENSE191_BASE_SHAPE_HOTPATH_MS:",
        "DENSE191_BASE_SHAPE_CACHE_MISSES:",
        "DENSE191_BASE_SHAPE_CACHE_HITS:",
        "DENSE191_PREPARE_BASE_REDUCTION_PCT:",
        "DENSE191_FINAL_PAIRS:",
        "NEXT_HOTSPOT:",
    ]:
        check(marker in code_report, f"report marker present: {marker}")

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
