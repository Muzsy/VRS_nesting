#!/usr/bin/env python3
"""Static semantic gate for SGH-Q25-R4.

This smoke intentionally does not run LV8 or any density benchmark. It checks the
source-level semantic fixes that Q25-R4 is about: rect-min sample-space convention,
LBF collision-invalid behavior, fixed-sheet bootstrap honesty, and report correction.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust/vrs_solver/src/optimizer/sparrow"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md"
Q25R3_REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md"

PASS = 0
FAIL = 0
WARN = 0

ALLOWED_PREFIXES = (
    "rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs",
    "rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs",
    "rust/vrs_solver/src/optimizer/sparrow/sample/search.rs",
    "rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs",
    "rust/vrs_solver/src/optimizer/sparrow/sample/uniform_sampler.rs",
    "rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs",
    "rust/vrs_solver/src/optimizer/sparrow/lbf.rs",
    "rust/vrs_solver/src/optimizer/sparrow/model.rs",
    "rust/vrs_solver/src/optimizer/sparrow/mod.rs",
    "rust/vrs_solver/src/optimizer/sparrow/tests.rs",
    "rust/vrs_solver/src/optimizer/cde_adapter.rs",
    "README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md",
    "canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md",
    "codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md",
    "codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml",
    "codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/",
    "codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md",
    "codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.verify.log",
    "scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py",
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


def main() -> int:
    print("SGH-Q25-R4 semantic parity audit/fix smoke")

    check(SP.exists(), "optimizer/sparrow module exists")
    report = read(REPORT)
    check(bool(report), "Q25-R4 report exists")
    warn(Q25R3_REPORT.exists(), "Q25-R3 report exists for claim-correction context")

    if report:
        required_headers = [
            "SGH-Q25-R4_STATUS",
            "UPSTREAM_COMMIT",
            "PRE_TASK_GIT_STATUS",
            "PRE_TASK_DIRTY_FILES",
            "PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES",
            "TASK_CHANGED_FILES",
            "OUT_OF_SCOPE_NEW_CHANGES",
            "ANCHOR_RECT_MIN_CONVENTION_AUDIT",
            "BEST_SAMPLES_SAMPLE_SPACE_AUDIT",
            "LBF_INVALID_SEMANTICS_AUDIT",
            "FIXED_SHEET_BOOTSTRAP_AUDIT",
            "Q25_R3_REPORT_CLAIM_CORRECTION",
            "LEGACY_CORE_REGRESSION_GATE",
            "TESTS_ADDED_OR_UPDATED",
            "BUILD_TEST_RESULTS",
        ]
        for header in required_headers:
            check(header in report, f"report contains {header}")
        pass_report = "SGH-Q25-R4_STATUS: PASS" in report
        if pass_report:
            for token in [
                "OUT_OF_SCOPE_NEW_CHANGES: NONE",
                "Q25_R3_LBF_REPORT_MISMATCH: CONFIRMED_AND_FIXED",
                "ANCHOR_RECT_MIN_CONVENTION: EXPLICIT_AND_TESTED",
                "LBF_COLLISION_SEMANTICS: INVALID_REJECTED",
                "COMPRESSION_STATUS: DEFERRED_ONLY",
                "LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE",
            ]:
                check(token in report, f"PASS report contains required token: {token}")
            forbidden = [
                "good enough", "future work", "not implemented", "benchmark improved",
                "lv8 pass", "dense tuning", "collision -> scored", "collision candidate accepted",
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

    sample_eval = rust("eval/sample_eval.rs")
    check("rect_min_x" in sample_eval and "rect_min_y" in sample_eval,
          "ScoredPlacement carries rect_min_x/rect_min_y sample-space coordinates")
    check("evaluate_sample" in sample_eval and "rect-min" in read(SP / "eval/sample_eval.rs").lower(),
          "SampleEvaluator documents rect-min input convention")

    lbf_eval = rust("eval/lbf_evaluator.rs")
    sep_eval = rust("eval/sep_evaluator.rs")
    check("rect_min_x" in lbf_eval and "rect_min_y" in lbf_eval,
          "LBFEvaluator fills rect-min sample-space fields")
    check("rect_min_x" in sep_eval and "rect_min_y" in sep_eval,
          "SeparationEvaluator fills rect-min sample-space fields")

    coord = rust("sample/coord_descent.rs")
    check("rect_min_x" in coord and "rect_min_y" in coord,
          "CoordinateDescent uses ScoredPlacement rect-min fields")
    check("rect_min_from_anchor" not in coord or "self.cur.placement.rotation_deg" not in coord,
          "CoordinateDescent does not repeatedly reconstruct sample-space from anchor with possibly wrong rotation")
    for banned in [
        "let tx = self.cur.placement.x",
        "let ty = self.cur.placement.y",
        "self.cur.placement.x + sx",
        "self.cur.placement.y + sy",
        "self.cur.placement.x - sx",
        "self.cur.placement.y - sy",
    ]:
        check(banned not in coord, f"CoordinateDescent avoids anchor translation state: {banned}")
    check("evaluate_sample" in coord, "CoordinateDescent still evaluates candidates through evaluator")

    best = rust("sample/best_samples.rs")
    check("rect_min_x" in best and "rect_min_y" in best,
          "BestSamples deduplicates by rect-min sample-space fields")
    for banned in [
        "s.placement.x - cand.placement.x",
        "s.placement.y - cand.placement.y",
        "placement.x -",
        "placement.y -",
    ]:
        check(banned not in best, f"BestSamples avoids anchor-space dedup: {banned}")

    search = rust("sample/search.rs")
    uniform = rust("sample/uniform_sampler.rs")
    check("ref_rect_min" in search and "rect_min_from_anchor" in search,
          "search boundary converts current anchor placement to rect-min reference")
    check("sample(" in uniform and "rect_min" in read(SP / "sample/uniform_sampler.rs").lower(),
          "UniformBBoxSampler emits rect-min samples")

    check("is_clear: false" not in lbf_eval,
          "LBFEvaluator does not emit colliding ScoredPlacement")
    for banned in [
        "1_000_000.0",
        "candidate_penalty",
        "overlap_score",
        "least_infeasible",
        "best_bad",
        "colliding_layout_idxs.len() as f64 * QUANT_FLOOR",
    ]:
        check(banned not in lbf_eval, f"LBFEvaluator avoids artificial collision-ranking branch: {banned}")
    check("return None" in lbf_eval or "SampleEval::Invalid" in lbf_eval,
          "LBFEvaluator rejects invalid/colliding candidates")

    lbf = rust("lbf.rs")
    fixed = rust("fixed_sheet.rs")
    check("fixed_sheet_separator_bootstrap" not in lbf,
          "fixed-sheet bootstrap is not embedded in LBFBuilder")
    check("fixed_sheet_separator_bootstrap" in fixed,
          "fixed-sheet bootstrap remains explicitly named outside LBF")
    check("unresolved" in lbf.lower(), "LBF records unresolved no-clear cases")

    tests = read(SP / "tests.rs")
    for name in [
        "coord_descent_uses_rect_min_for_rotated_anchor_candidates",
        "best_samples_deduplicates_in_rect_min_sample_space",
        "lbf_evaluator_rejects_colliding_candidates_as_invalid",
        "fixed_sheet_bootstrap_is_outside_lbf_and_marked_infeasible",
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
    sys.exit(main())
