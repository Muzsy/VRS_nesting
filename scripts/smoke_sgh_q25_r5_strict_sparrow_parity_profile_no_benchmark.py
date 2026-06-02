#!/usr/bin/env python3
"""Static semantic gate for SGH-Q25-R5.

This smoke is intentionally source-level and benchmark-free. It verifies that the
strict Sparrow parity profile exists and that the common regressions identified
after Q25-R4 cannot pass silently.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust/vrs_solver/src/optimizer/sparrow"
CDE = ROOT / "rust/vrs_solver/src/optimizer/cde_adapter.rs"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md"

PASS = 0
FAIL = 0
WARN = 0

ALLOWED_PREFIXES = (
    "rust/vrs_solver/src/optimizer/cde_adapter.rs",
    "rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs",
    "rust/vrs_solver/src/optimizer/sparrow/model.rs",
    "rust/vrs_solver/src/optimizer/sparrow/optimizer.rs",
    "rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/lbf.rs",
    "rust/vrs_solver/src/optimizer/sparrow/sample/search.rs",
    "rust/vrs_solver/src/optimizer/sparrow/separator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/worker.rs",
    "rust/vrs_solver/src/optimizer/sparrow/explore.rs",
    "rust/vrs_solver/src/optimizer/sparrow/tests.rs",
    "README_SGH_Q25_R5_STRICT_SPARROW_PARITY_PROFILE_PACKAGE.md",
    "canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md",
    "codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md",
    "codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml",
    "codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/",
    "codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md",
    "codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.verify.log",
    "scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py",
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


def main() -> int:
    print("SGH-Q25-R5 strict Sparrow parity profile smoke")

    check(SP.exists(), "optimizer/sparrow module exists")
    check(CDE.exists(), "cde_adapter.rs exists")
    report = read(REPORT)
    check(bool(report), "Q25-R5 report exists")

    if report:
        required_headers = [
            "SGH-Q25-R5_STATUS",
            "UPSTREAM_COMMIT",
            "PRE_TASK_GIT_STATUS",
            "PRE_TASK_DIRTY_FILES",
            "PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES",
            "TASK_CHANGED_FILES",
            "OUT_OF_SCOPE_NEW_CHANGES",
            "STRICT_PROFILE_CONFIG_AUDIT",
            "TOUCHING_POLICY_AUDIT",
            "SAMPLE_BUDGET_AUDIT",
            "WORKER_ORDERING_AUDIT",
            "SEPARATOR_LOOP_AUDIT",
            "EXPLORATION_DISRUPTION_AUDIT",
            "FIXED_SHEET_ADAPTATION_BOUNDARY",
            "LEGACY_CORE_REGRESSION_GATE",
            "TESTS_ADDED_OR_UPDATED",
            "BUILD_TEST_RESULTS",
        ]
        for header in required_headers:
            check(header in report, f"report contains {header}")
        pass_report = "SGH-Q25-R5_STATUS: PASS" in report
        if pass_report:
            for token in [
                "STRICT_PROFILE_DEFAULT: SPARROW_STRICT_PARITY",
                "TOUCHING_POLICY_STRICT: CDE_TOUCHING_IS_COLLISION",
                "VRS_TOUCH_ALLOWED_POLICY: EXPLICIT_NON_PARITY_MODE",
                "SAMPLE_BUDGETS: UPSTREAM_PARITY",
                "INSTANCE_COUNT_DOWNSCALING: DISABLED_IN_STRICT_PROFILE",
                "WORKER_ORDERING: RNG_SHUFFLE_ONLY_IN_STRICT_PROFILE",
                "SEPARATOR_LIMITS: UPSTREAM_PARITY_200_3",
                "EXPLORATION_RESTORE: NORMAL_BIASED_POOL_SELECTION",
                "DISRUPTION_SWAP: RANDOM_LARGE_ITEM_PAIR",
                "COMPRESSION_STATUS: DEFERRED_ONLY",
                "LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE",
                "OUT_OF_SCOPE_NEW_CHANGES: NONE",
            ]:
                check(token in report, f"PASS report contains required token: {token}")
            forbidden = [
                "good enough", "future work", "not implemented", "benchmark improved",
                "lv8 pass", "dense tuning", "touching allowed in parity", "maybe parity",
            ]
            for word in forbidden:
                check(word.lower() not in report.lower(), f"PASS report avoids forbidden wording: {word}")

    status_files = git_status_files()
    if status_files:
        out_of_scope = [p for p in status_files if not allowed(p)]
        unreported = [p for p in out_of_scope if not report_mentions(p, report)]
        check(not unreported, "all current out-of-scope dirty files are pre-reported or absent")
    else:
        warn(False, "git status unavailable or clean; scope gate checked by report only")

    diagnostics = rust("diagnostics.rs")
    check("SparrowStrictParity" in diagnostics or "StrictParity" in diagnostics,
          "strict Sparrow parity profile exists in config/diagnostics")
    check("VrsFast" in diagnostics or "Fast" in diagnostics or "VrsTouchAllowed" in read(CDE),
          "non-parity VRS/fast/touch mode is explicit if retained")

    required_consts = {
        "SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES": "50",
        "SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES": "25",
        "SPARROW_PARITY_COORD_DESCENTS": "3",
        "SPARROW_PARITY_LBF_CONTAINER_SAMPLES": "1000",
        "SPARROW_PARITY_LBF_FOCUSED_SAMPLES": "0",
        "SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT": "200",
        "SPARROW_PARITY_STRIKE_LIMIT": "3",
        "SPARROW_PARITY_WORKERS": "3",
        "SPARROW_PARITY_MAX_CONSEC_FAILED_ATTEMPTS": "10",
        "SPARROW_PARITY_SOLUTION_POOL_STDDEV": "0.25",
        "SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE": "0.75",
    }
    for name, value in required_consts.items():
        check(has_const(read(SP / "diagnostics.rs"), name, value), f"strict constant {name} = {value}")

    cde = strip_comments(read(CDE))
    raw_cde = read(CDE)
    check("CdeTouchingPolicy" in raw_cde, "CdeTouchingPolicy enum/type exists")
    check("SparrowStrict" in raw_cde, "SparrowStrict touching policy exists")
    check("VrsTouchAllowed" in raw_cde, "VrsTouchAllowed explicit non-parity policy exists")
    check("touching_policy" in raw_cde, "touching policy is carried by config/session")
    check(raw_cde.count("SparrowStrict") >= 3, "SparrowStrict is wired, not just declared")
    check(raw_cde.count("VrsTouchAllowed") >= 3, "VrsTouchAllowed is wired, not just declared")
    # Old ambiguous comments are a strong sign that touching is still implicit.
    for old in [
        "touching edge/corner → NoCollision",
        "touching boundary is allowed",
        "touching the boundary edge is not a crossing",
    ]:
        check(old not in raw_cde, f"old implicit touch-allowed comment removed/qualified: {old}")

    lbf = rust("lbf.rs")
    search = rust("sample/search.rs")
    sep = rust("separator.rs")
    worker = rust("worker.rs")
    explore = rust("explore.rs")
    optimizer = rust("optimizer.rs")

    check("SPARROW_PARITY_LBF_CONTAINER_SAMPLES" in lbf and "SPARROW_PARITY_COORD_DESCENTS" in lbf,
          "LBF sample config uses strict upstream constants")
    check("n_container_samples: 128" not in lbf, "LBF no longer uses 128-sample local shortcut")
    check("SPARROW_PARITY_SEPARATOR_CONTAINER_SAMPLES" in search, "separator search uses strict container-sample constant")
    check("SPARROW_PARITY_SEPARATOR_FOCUSED_SAMPLES" in search, "separator search uses strict focused-sample constant")
    check("SPARROW_PARITY_COORD_DESCENTS" in search, "separator search uses strict coord-descent constant")
    check("global_grid_n * global_grid_n" not in search or "StrictParity" in search,
          "strict search no longer derives parity samples from local grid shortcut")
    check("SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT" in sep, "separator uses strict no-improvement constant")
    check("SPARROW_PARITY_STRIKE_LIMIT" in sep, "separator uses strict strike constant")
    for banned in ["no_improve_limit = 6", "strike_limit = 4"]:
        check(banned not in sep, f"separator avoids old hard-coded limit: {banned}")

    check("StrictParity" in diagnostics and ("scaled_for_instance_count" in diagnostics),
          "scaled_for_instance_count explicitly handles strict parity")
    check("INSTANCE_COUNT_DOWNSCALING: DISABLED_IN_STRICT_PROFILE" in report if report else False,
          "report states strict profile disables instance-count downscaling")

    check("rng.shuffle(&mut colliding)" in worker, "worker shuffles colliding items with RNG")
    for banned in ["worker_idx %", "colliding.reverse", "worst-first", "least-loss", "higher even workers"]:
        check(banned not in worker, f"strict worker ordering avoids worker-index bias: {banned}")

    check("SPARROW_PARITY_MAX_CONSEC_FAILED_ATTEMPTS" in explore, "exploration uses strict max failed attempts constant")
    check("SPARROW_PARITY_SOLUTION_POOL_STDDEV" in explore, "exploration uses strict pool stddev constant")
    check("SPARROW_PARITY_LARGE_ITEM_CH_AREA_CUTOFF_PERCENTILE" in explore,
          "disruption uses strict large-item cutoff percentile constant")
    for banned in ["wrapping_add(attempt)", "% ((infeas_sol_pool.len() + 1) / 2)", "by_area[0]", "by_area[1]"]:
        check(banned not in explore, f"exploration/disruption avoids deterministic shortcut: {banned}")
    check("select_large_item_swap_pair" in explore or "random_large_item" in explore.lower(),
          "exploration has named random large-item pair selection helper")
    check("biased_pool" in explore.lower() or "normal" in explore.lower(),
          "exploration has named biased pool restore logic")

    tests = read(SP / "tests.rs")
    for name in [
        "cde_sparrow_strict_reports_touching_rectangles_as_collision",
        "cde_vrs_touch_allowed_reports_touching_rectangles_as_no_collision",
        "sparrow_strict_boundary_touching_is_not_feasible",
        "strict_worker_orders_colliding_items_by_rng_shuffle_only",
        "strict_separator_uses_upstream_loop_limits",
        "strict_explore_uses_biased_pool_restore_not_seed_modulo",
        "strict_disruption_selects_random_large_item_pair_not_always_top_two",
        "fixed_sheet_extensions_are_documented_after_upstream_swap",
    ]:
        check(name in tests, f"targeted Rust test exists: {name}")

    allsrc = all_sparrow()
    check("WorkingLayout" not in allsrc, "optimizer/sparrow does not use WorkingLayout")
    check("VrsCollisionTracker" not in allsrc, "optimizer/sparrow does not use VrsCollisionTracker")
    check("compression_phase" not in allsrc and "compression_pass" not in allsrc,
          "compression remains excluded")
    for banned in ["aabb_penetration", "hazard_extent_depth", "candidate_penalty", "overlap_score"]:
        check(banned not in allsrc, f"no banned proxy/ranking token in optimizer/sparrow: {banned}")

    print(f"\nSummary: PASS={PASS} WARN={WARN} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
