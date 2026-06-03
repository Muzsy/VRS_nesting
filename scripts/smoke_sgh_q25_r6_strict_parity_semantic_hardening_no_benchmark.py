#!/usr/bin/env python3
"""Static semantic gate for SGH-Q25-R6.

This smoke is intentionally benchmark-free. It verifies the narrow Q25-R6 scope:
convex-hull large-item disruption, strict touching edge-case tests, upstream mapping
report, and no regression of Q25-R5 strict profile invariants.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust/vrs_solver/src/optimizer/sparrow"
CDE = ROOT / "rust/vrs_solver/src/optimizer/cde_adapter.rs"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md"

PASS = 0
FAIL = 0
WARN = 0

ALLOWED_PREFIXES = (
    "rust/vrs_solver/src/optimizer/cde_adapter.rs",
    "rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs",
    "rust/vrs_solver/src/optimizer/sparrow/explore.rs",
    "rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/tests.rs",
    "README_SGH_Q25_R6_STRICT_PARITY_SEMANTIC_HARDENING_PACKAGE.md",
    "canvases/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md",
    "codex/codex_checklist/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md",
    "codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.yaml",
    "codex/prompts/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark/",
    "codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.md",
    "codex/reports/egyedi_solver/sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.verify.log",
    "scripts/smoke_sgh_q25_r6_strict_parity_semantic_hardening_no_benchmark.py",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_comments(text: str) -> str:
    text = re.sub(r"(?m)//.*$", "", text)
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    return text


def rust(rel: str) -> str:
    return strip_comments(read(SP / rel))


def all_sparrow() -> str:
    return "\n".join(strip_comments(read(p)) for p in SP.rglob("*.rs")) if SP.exists() else ""


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def warn(cond: bool, msg: str) -> None:
    global PASS, WARN
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        WARN += 1
        print(f"  [WARN] {msg}")


def git_status_files() -> list[str]:
    try:
        cp = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        return []
    files: list[str] = []
    for line in cp.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def allowed(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in ALLOWED_PREFIXES)


def report_mentions(path: str, report: str) -> bool:
    return path in report


def has_const(text: str, name: str, value: str) -> bool:
    pat = rf"pub\s+const\s+{re.escape(name)}\s*:\s*(?:usize|f64)\s*=\s*{re.escape(value)}\s*;"
    return re.search(pat, text) is not None


def function_body(text: str, fn_name: str) -> str:
    # Small brace matcher; sufficient for Rust source static gate.
    marker = re.search(rf"fn\s+{re.escape(fn_name)}\s*\([^)]*\)[^{{]*{{", text)
    if not marker:
        marker = re.search(rf"pub\(super\)\s+fn\s+{re.escape(fn_name)}\s*\([^)]*\)[^{{]*{{", text)
    if not marker:
        return ""
    start = marker.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def main() -> int:
    print("SGH-Q25-R6 strict parity semantic hardening smoke")

    check(SP.exists(), "optimizer/sparrow module exists")
    check(CDE.exists(), "cde_adapter.rs exists")
    report = read(REPORT)
    check(bool(report), "Q25-R6 report exists")

    if report:
        required_headers = [
            "SGH-Q25-R6_STATUS",
            "UPSTREAM_COMMIT",
            "PRE_TASK_GIT_STATUS",
            "PRE_TASK_DIRTY_FILES",
            "PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES",
            "TASK_CHANGED_FILES",
            "OUT_OF_SCOPE_NEW_CHANGES",
            "CONVEX_HULL_DISRUPTION_AUDIT",
            "STRICT_TOUCHING_EDGE_CASE_AUDIT",
            "UPSTREAM_LINE_MAPPING_AUDIT",
            "Q25_R5_INVARIANT_REGRESSION_AUDIT",
            "LEGACY_CORE_REGRESSION_GATE",
            "TESTS_ADDED_OR_UPDATED",
            "BUILD_TEST_RESULTS",
        ]
        for header in required_headers:
            check(header in report, f"report contains {header}")

        if "SGH-Q25-R6_STATUS: PASS" in report:
            for token in [
                "CONVEX_HULL_AREA_KEY: USED_FOR_STRICT_LARGE_ITEM_DISRUPTION",
                "BBOX_WIDTH_HEIGHT_PRODUCT: NOT_USED_FOR_STRICT_LARGE_ITEM_CUTOFF",
                "STRICT_TOUCHING_TESTS: EDGE_CORNER_BOUNDARY_EPSILON_COVERED",
                "UPSTREAM_MAPPING: LINE_BY_LINE_RECHECKED",
                "Q25_R5_STRICT_PROFILE_INVARIANTS: PRESERVED",
                "COMPRESSION_STATUS: DEFERRED_ONLY",
                "LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE",
                "OUT_OF_SCOPE_NEW_CHANGES: NONE",
            ]:
                check(token in report, f"PASS report contains required token: {token}")

            forbidden = [
                "future work", "not implemented", "benchmark improved", "lv8 pass",
                "dense tuning", "touching allowed in parity", "maybe parity",
                "could not verify upstream",
            ]
            for word in forbidden:
                check(word.lower() not in report.lower(), f"PASS report avoids forbidden wording: {word}")

        mapping_tokens = [
            ".cache/sparrow/src/optimizer/explore.rs",
            ".cache/sparrow/src/optimizer/worker.rs",
            ".cache/sparrow/src/optimizer/separator.rs",
            ".cache/sparrow/src/sample/search.rs",
            ".cache/sparrow/src/optimizer/lbf.rs",
            ".cache/sparrow/src/eval/sep_evaluator.rs",
            ".cache/sparrow/src/eval/lbf_evaluator.rs",
            ".cache/sparrow/src/consts.rs",
            ".cache/sparrow/src/config.rs",
            "ADAPTED_FIXED_SHEET",
            "PORTED",
        ]
        for token in mapping_tokens:
            check(token in report, f"upstream mapping report contains {token}")

    status_files = git_status_files()
    if status_files:
        out_of_scope = [p for p in status_files if not allowed(p)]
        unreported = [p for p in out_of_scope if not report_mentions(p, report)]
        check(not unreported, "all current out-of-scope dirty files are pre-reported or absent")
    else:
        warn(False, "git status unavailable or clean; scope gate checked by report only")

    diagnostics = rust("diagnostics.rs")
    for name, value in {
        "SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES": "50",
        "SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES": "25",
        "SPARROW_PARITY_COORD_DESCENTS": "3",
        "SPARROW_PARITY_LBF_CONTAINER_SAMPLES": "1000",
        "SPARROW_PARITY_LBF_FOCUSED_SAMPLES": "0",
        "SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT": "200",
        "SPARROW_PARITY_STRIKE_LIMIT": "3",
        "SPARROW_PARITY_WORKERS": "3",
        "SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE": "0.75",
    }.items():
        check(has_const(diagnostics, name, value), f"Q25-R5 strict invariant constant {name} = {value}")

    cde_raw = read(CDE)
    check("CdeTouchingPolicy" in cde_raw, "CdeTouchingPolicy still exists")
    check("SparrowStrict" in cde_raw, "SparrowStrict touching policy still exists")
    check("VrsTouchAllowed" in cde_raw, "VrsTouchAllowed explicit non-parity policy still exists")

    explore = rust("explore.rs")
    select_body = function_body(explore, "select_large_item_swap_pair")
    check("large_item_disruption_area_key" in explore, "large_item_disruption_area_key helper exists")
    check(
        "convex_hull_area_and_diameter" in explore or "convex_hull_area" in explore,
        "explore/disruption uses convex hull area source",
    )
    check(
        "SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE" in select_body,
        "large-item selector still uses 0.75 parity cutoff constant",
    )
    check(
        "width * inst.part.height" not in select_body and "part.width * part.height" not in select_body,
        "select_large_item_swap_pair normal path does not use bbox width*height product",
    )
    check(
        "large_item_disruption_area_key" in select_body,
        "select_large_item_swap_pair calls convex-hull disruption key helper",
    )
    check(
        "fallback" in explore.lower() and ("width" in explore and "height" in explore),
        "bbox fallback, if present, is explicit/commented rather than silent",
    )

    tests = read(SP / "tests.rs")
    required_tests = [
        "strict_large_item_disruption_uses_convex_hull_area_not_bbox_area",
        "strict_large_item_cutoff_uses_cumulative_convex_hull_area_percentile",
        "strict_large_item_bbox_fallback_is_only_for_unprepared_shape",
        "strict_pair_edge_touching_is_collision",
        "strict_pair_corner_touching_is_collision",
        "vrs_touch_allowed_pair_edge_and_corner_touching_are_clear",
        "strict_boundary_exact_fit_is_not_feasible",
        "strict_boundary_epsilon_inside_is_feasible",
        "strict_boundary_epsilon_outside_is_collision",
    ]
    for name in required_tests:
        check(name in tests, f"Rust test exists: {name}")

    check(
        any(token in tests.lower() for token in ["triangle", "l_shape", "l-shape", "irregular", "concave"]),
        "tests include an irregular/non-rectangular fixture for convex-hull vs bbox behavior",
    )
    check("epsilon" in tests.lower() or "1e-" in tests, "boundary tests include epsilon inside/outside cases")

    worker = rust("worker.rs")
    check("rng.shuffle" in worker or ".shuffle(" in worker, "strict worker RNG shuffle remains present")
    separator = rust("separator.rs")
    check("SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT" in separator, "strict separator 200 limit still wired")
    check("SPARROW_PARITY_STRIKE_LIMIT" in separator, "strict separator 3 strike limit still wired")

    combined = all_sparrow()
    for forbidden in ["WorkingLayout", "VrsCollisionTracker"]:
        check(forbidden not in combined, f"legacy {forbidden} absent from optimizer/sparrow")
    for forbidden in ["compression_phase", "CompressionPhase", "run_compression"]:
        check(forbidden not in combined, f"compression hook absent: {forbidden}")
    for forbidden in ["lv8", "191", "full_276"]:
        check(forbidden not in combined.lower(), f"no LV8 benchmark gate token in optimizer/sparrow: {forbidden}")

    print(f"\nSGH-Q25-R6 smoke result: PASS={PASS} WARN={WARN} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
