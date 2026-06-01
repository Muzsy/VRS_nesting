#!/usr/bin/env python3
"""SGH-Q25-R2 complete upstream Sparrow core semantic port smoke.

This smoke intentionally checks the failure mode that caused earlier tasks to
pass while still keeping local/proxy semantics. It is not a benchmark smoke.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow"
REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md"

PASS = 0
FAIL = 0
WARN = 0

ALLOWED_PREFIXES = (
    "rust/vrs_solver/src/optimizer/sparrow/",
    "rust/vrs_solver/src/optimizer/cde_adapter.rs",
    "rust/vrs_solver/src/optimizer/cde_session.rs",
    "rust/vrs_solver/src/optimizer/cde_observability.rs",
    "rust/vrs_solver/src/optimizer/collision_severity.rs",
    "README_SGH_Q25_R2_COMPLETE_UPSTREAM_SPARROW_CORE_SEMANTIC_PORT_PACKAGE.md",
    "canvases/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md",
    "codex/codex_checklist/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md",
    "codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.yaml",
    "codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/",
    "codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md",
    "codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.verify.log",
    "scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_comments(text: str) -> str:
    text = re.sub(r"(?m)//.*$", "", text)
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    return text


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


def rust(rel: str) -> str:
    return strip_comments(read(SP / rel))


def all_sparrow() -> str:
    if not SP.exists():
        return ""
    return "\n".join(strip_comments(read(p)) for p in SP.rglob("*.rs"))


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


def section_present(report: str, header: str) -> bool:
    return header in report


def main() -> int:
    print("SGH-Q25-R2 complete upstream Sparrow core semantic port smoke")

    check(SP.exists(), "optimizer/sparrow module exists")

    report = read(REPORT)
    check(bool(report), "Q25-R2 report exists")
    if report:
        check("SGH-Q25-R2_STATUS:" in report, "report has status marker")
        for header in [
            "UPSTREAM_COMMIT",
            "PRE_TASK_GIT_STATUS",
            "PRE_TASK_DIRTY_FILES",
            "PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES",
            "TASK_CHANGED_FILES",
            "OUT_OF_SCOPE_NEW_CHANGES",
            "SEMANTIC_MAPPING_TABLE",
        ]:
            check(section_present(report, header), f"report contains {header}")
        check("Upstream file | Upstream type/function | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence" in report,
              "report contains required mapping table header")
        check("Sparrow-like" not in report and "good enough" not in report.lower() and "benchmark improved" not in report.lower(),
              "report avoids vague/benchmark pass language")

    status_files = git_status_files()
    if status_files:
        out_of_scope = [p for p in status_files if not allowed(p)]
        unreported = [p for p in out_of_scope if not report_mentions(p, report)]
        check(not unreported, "all current out-of-scope dirty files are pre-reported or absent")
    else:
        warn(False, "git status unavailable or clean; scope gate checked by report only")

    required_files = [
        "eval/specialized_cde_pipeline.rs",
        "eval/sep_evaluator.rs",
        "eval/lbf_evaluator.rs",
        "eval/sample_eval.rs",
        "quantify/mod.rs",
        "quantify/tracker.rs",
        "quantify/overlap_proxy.rs",
        "sample/search.rs",
        "sample/coord_descent.rs",
        "sample/best_samples.rs",
        "sample/uniform_sampler.rs",
        "lbf.rs",
        "worker.rs",
        "separator.rs",
        "explore.rs",
        "optimizer.rs",
    ]
    for rel in required_files:
        check((SP / rel).exists(), f"required upstream-mapped local file exists: {rel}")

    allsrc = all_sparrow()
    check("WorkingLayout" not in allsrc and "VrsCollisionTracker" not in allsrc,
          "optimizer/sparrow does not use old VRS core model")
    check("compression_phase" not in allsrc and "compression_pass" not in allsrc,
          "compression remains excluded from optimizer/sparrow")

    specialized = rust("eval/specialized_cde_pipeline.rs")
    check("SpecializedCdeHazardCollector" in specialized, "specialized collector exists")
    check("loss_bound" in specialized and "early_terminate" in specialized,
          "collector has bound and early-termination state")
    check("session.query(candidate)" not in specialized and ".query(candidate)" not in specialized,
          "specialized collector is not post-query-only batch accumulation")
    check(any(tok in specialized for tok in ["collect_with", "collect_bounded", "visit", "HazardCollector", "collect_poly_collisions"]),
          "specialized collector uses a collection/visitor-style CDE path")

    sep_eval = rust("eval/sep_evaluator.rs")
    check("SpecializedCdeHazardCollector" in sep_eval and "reload" in sep_eval,
          "SeparationEvaluator uses specialized collector reload")
    check("upper_bound" in sep_eval or "loss_bound" in sep_eval,
          "SeparationEvaluator passes an upper/loss bound")
    for banned in ["aabb_penetration", "hazard_extent_depth", "ox.min(oy)", "ix * iy", "overlap_score", "candidate_penalty"]:
        check(banned not in sep_eval, f"SeparationEvaluator avoids banned proxy ranking: {banned}")

    quant = rust("quantify/mod.rs") + "\n" + rust("quantify/overlap_proxy.rs")
    tracker = rust("quantify/tracker.rs")
    check("overlap_area_proxy" in quant, "quantification has upstream overlap_area_proxy")
    check("shape_penalty" in quant or "calc_shape_penalty" in quant,
          "quantification includes shape penalty")
    check("resolution_distance" not in allsrc.lower() and "probe_pair_resolution" not in allsrc.lower(),
          "production sparrow sources no longer expose resolution-distance default semantics")
    for tok in ["pair_loss", "boundary_loss", "item_weighted_loss", "total_weighted_loss", "update_weights"]:
        check(tok in tracker, f"tracker exposes/uses {tok}")

    lbf = rust("lbf.rs")
    for banned in [
        "shelf_construct",
        "fallback_anchor",
        "fixed_sheet_recovery_candidate",
        "candidate_penalty",
        "overlap_score",
        "least_infeasible",
        "least-infeasible",
    ]:
        check(banned not in lbf, f"LBF does not contain banned constructive shortcut: {banned}")
    check("search_placement" in lbf and "LBFEvaluator" in lbf,
          "LBF uses search_placement + LBFEvaluator")
    check(any(tok in lbf.lower() for tok in ["unresolved", "partial", "no_clear"]),
          "LBF has honest unresolved/partial handling for no-clear fixed-sheet cases")

    search = rust("sample/search.rs")
    check("BestSamples" in search and "Uniform" in search,
          "search uses BestSamples and uniform/container-wide sampling")
    check("focused" in search.lower(), "search includes focused sampling")
    check("coordinate" in search.lower() or "coord" in search.lower(), "search invokes coordinate descent/refinement")
    check("dense" not in search.lower() or "benchmark" not in search.lower(),
          "search is not dense-benchmark shortcut driven")

    coord = rust("sample/coord_descent.rs")
    check("dr" in coord or "rotation" in coord.lower(), "coordinate descent supports rotation refinement")
    check(any(tok in coord.lower() for tok in ["success", "fail", "step"]),
          "coordinate descent has success/fail step semantics")

    worker = rust("worker.rs")
    check("weighted" in worker.lower(), "worker uses weighted loss semantics")
    check("new_pairs" not in worker and "pair_count" not in worker.lower(),
          "worker does not accept by pair-count shortcuts")

    separator = rust("separator.rs")
    check("total_weighted_loss" in separator or "weighted_loss" in separator,
          "separator carries total weighted loss")
    check("min_by" in separator and "weighted" in separator.lower(),
          "separator best-worker selection is weighted-loss based")
    check("colliding_pairs" not in separator or "tie" in separator.lower() or "diagnostic" in separator.lower(),
          "pair count is not primary separator selection")

    explore = rust("explore.rs")
    check("pool" in explore.lower() and "restore" in explore.lower(),
          "exploration has pool/restore logic")
    check("contained" in explore.lower() and ("cde" in explore.lower() or "geometry" in explore.lower() or "polygon" in explore.lower()),
          "exploration has geometry/CDE meaningful contained-item relocation")

    print(f"\nResult: PASS={PASS} FAIL={FAIL} WARN={WARN}")
    if FAIL:
        print("SGH-Q25-R2 smoke: FAIL")
        return 1
    print("SGH-Q25-R2 smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
