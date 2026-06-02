#!/usr/bin/env python3
"""Static smoke for SGH-Q25-R3 upstream Sparrow port closure.

This smoke intentionally checks for semantic-port closure signals, not benchmark
quality. It is conservative: it catches the common escape hatches that caused the
previous tasks to pass while still leaving Sparrow-like local approximations.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust/vrs_solver/src/optimizer/sparrow"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md"

PASS = 0
FAIL = 0
WARN = 0

ALLOWED_PREFIXES = (
    "rust/vrs_solver/src/optimizer/sparrow/",
    "rust/vrs_solver/src/optimizer/cde_adapter.rs",
    "rust/vrs_solver/src/optimizer/cde_session.rs",
    "rust/vrs_solver/src/optimizer/cde_observability.rs",
    "rust/vrs_solver/src/optimizer/collision_severity.rs",
    "README_SGH_Q25_R3_UPSTREAM_SPARROW_PORT_CLOSURE_PACKAGE.md",
    "canvases/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md",
    "codex/codex_checklist/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md",
    "codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.yaml",
    "codex/prompts/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark/",
    "codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md",
    "codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.verify.log",
    "scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py",
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
    if not SP.exists():
        return ""
    return "\n".join(strip_comments(read(p)) for p in SP.rglob("*.rs"))


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
    print("SGH-Q25-R3 upstream Sparrow port closure smoke")

    check(SP.exists(), "optimizer/sparrow module exists")
    report = read(REPORT)
    check(bool(report), "Q25-R3 report exists")
    if report:
        for header in [
            "SGH-Q25-R3_STATUS",
            "UPSTREAM_COMMIT",
            "PRE_TASK_GIT_STATUS",
            "PRE_TASK_DIRTY_FILES",
            "PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES",
            "TASK_CHANGED_FILES",
            "OUT_OF_SCOPE_NEW_CHANGES",
            "PORT_CLOSURE_MAPPING_TABLE",
            "FIXED_SHEET_DEVIATIONS_WITH_NO_SEMANTIC_LOSS",
            "DEFERRED_COMPRESSION_ONLY",
            "BUILD_TEST_RESULTS",
        ]:
            check(header in report, f"report contains {header}")
        check(
            "Upstream file | Upstream behavior | Local file/function | Status | Allowed deviation | Evidence" in report,
            "report has required port-closure mapping table header",
        )
        forbidden_pass_words = [
            "PARTIAL", "TODO", "STUB", "PROXY", "PERF_ONLY_SKIP",
            "ADAPTED_APPROXIMATION", "future work", "not implemented",
            "pole pre-pass is skipped", "pole prepass is skipped", "skipped pole",
            "benchmark improved", "good enough", "Sparrow-like",
        ]
        if "SGH-Q25-R3_STATUS: PASS" in report:
            for word in forbidden_pass_words:
                check(word.lower() not in report.lower(), f"PASS report avoids forbidden gap wording: {word}")
        check("OUT_OF_SCOPE_NEW_CHANGES" in report and "NONE" in report.split("OUT_OF_SCOPE_NEW_CHANGES", 1)[1][:300],
              "report declares no out-of-scope new changes near OUT_OF_SCOPE_NEW_CHANGES")

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
        "quantify/overlap_proxy.rs",
        "quantify/tracker.rs",
        "sample/search.rs",
        "sample/uniform_sampler.rs",
        "sample/coord_descent.rs",
        "sample/best_samples.rs",
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
          "collector has loss-bound/early termination state")
    check("session.query(candidate)" not in specialized and ".query(candidate)" not in specialized,
          "specialized collector is not post-query-only batch accumulation")
    check("pole" in specialized.lower(), "specialized pipeline contains pole pre-pass logic")
    check(any(tok in specialized for tok in ["area_threshold", "area_sum", "0.5"]),
          "pole pre-pass has upstream area-threshold concept")
    check(any(tok in specialized.lower() for tok in ["bit_reversal", "bitreversal", "bit-reversal", "bit_reversed"]),
          "specialized pipeline keeps bit-reversed edge traversal")
    check("contain" in specialized.lower(), "specialized pipeline has containment pass")
    for banned in ["perf-only", "future work", "skipped", "omitted"]:
        check(banned not in specialized.lower(), f"specialized pipeline does not excuse missing behavior: {banned}")

    sep_eval = rust("eval/sep_evaluator.rs")
    check("SpecializedCdeHazardCollector" in sep_eval and "reload" in sep_eval,
          "SeparationEvaluator uses specialized collector reload")
    check("upper_bound" in sep_eval or "loss_bound" in sep_eval,
          "SeparationEvaluator passes upper/loss bound")
    for banned in ["aabb_penetration", "hazard_extent_depth", "candidate_penalty", "overlap_score", "ix * iy"]:
        check(banned not in sep_eval, f"SeparationEvaluator avoids banned proxy ranking: {banned}")

    quant = rust("quantify/overlap_proxy.rs") + "\n" + rust("quantify/mod.rs")
    tracker = rust("quantify/tracker.rs")
    check("overlap_area_proxy" in quant, "quantification uses upstream overlap_area_proxy")
    check("shape_penalty" in quant or "calc_shape_penalty" in quant, "quantification includes shape penalty")
    check("resolution_distance" not in allsrc.lower() and "probe_pair_resolution" not in allsrc.lower(),
          "production sparrow sources do not expose resolution-distance default semantics")
    for tok in ["pair_loss", "boundary_loss", "item_weighted_loss", "total_weighted_loss", "update_weights"]:
        check(tok in tracker, f"tracker exposes/uses {tok}")

    lbf = rust("lbf.rs")
    for banned in [
        "shelf_construct", "fallback_anchor", "fixed_sheet_recovery_candidate",
        "candidate_penalty", "overlap_score", "least_infeasible", "least-infeasible",
        "best_bad", "best-bad", "samples_for(rot, 1", "instances.len() >= 100",
    ]:
        check(banned not in lbf, f"LBF avoids banned shortcut: {banned}")
    check("search_placement" in lbf and "LBFEvaluator" in lbf,
          "LBF uses search_placement + LBFEvaluator")
    check(any(tok in lbf.lower() for tok in ["convex", "surrogate", "hull"]) and "diameter" in lbf.lower(),
          "LBF ordering is upstream convex-hull-area × diameter equivalent")
    check("seed_unresolved_on_fixed_sheets" not in lbf,
          "fixed-sheet infeasible bootstrap is not embedded in LBFBuilder")
    check(any(tok in lbf.lower() for tok in ["unresolved", "no_clear", "no clear"]),
          "LBF honestly records unresolved no-clear fixed-sheet cases")

    uniform = rust("sample/uniform_sampler.rs")
    check("rot_entries" in uniform or "RotEntry" in uniform, "UniformBBoxSampler stores rotation entries")
    check("ROT_N_SAMPLES" in uniform and "16" in uniform, "UniformBBoxSampler has 16 continuous rotation samples")
    check("Continuous" in uniform or "continuous" in uniform.lower(), "UniformBBoxSampler handles continuous rotations")
    check("Discrete" in uniform or "allowed_rotations" in uniform, "UniformBBoxSampler handles discrete rotations")
    check("intersect" in uniform.lower() and "range" in uniform.lower(),
          "UniformBBoxSampler intersects valid x/y ranges")
    check("rng" in uniform.lower() and "random" in uniform.lower(),
          "UniformBBoxSampler randomly samples valid ranges, not grid-only")

    search = rust("sample/search.rs")
    check("BestSamples" in search, "search uses BestSamples")
    check("focused" in search.lower(), "search has focused sampler concept")
    check(any(tok in search.lower() for tok in ["container", "sheet"]), "search has container-wide/fixed-sheet sampling concept")
    check("UniformBBoxSampler" in search, "search uses UniformBBoxSampler")
    check("refine" in search.lower() and ("pre" in search.lower() or "first" in search.lower()) and ("final" in search.lower() or "second" in search.lower()),
          "search has two-stage coordinate descent/refinement")
    check("current" in search.lower() or "reference" in search.lower() or "ref_" in search.lower(),
          "search considers current/reference placement candidate")
    check("dense" not in search.lower() and "benchmark" not in search.lower(),
          "search has no dense-benchmark shortcut language")

    coord = rust("sample/coord_descent.rs")
    check("rotation" in coord.lower() or "wiggle" in coord.lower() or "dr" in coord,
          "coordinate descent supports rotation wiggle/refinement")
    check(any(tok in coord.lower() for tok in ["success", "fail"]) and "step" in coord.lower(),
          "coordinate descent has success/fail step semantics")

    worker = rust("worker.rs")
    check("weighted" in worker.lower(), "worker uses weighted-loss semantics")
    check("pair_count" not in worker.lower() and "new_pairs" not in worker,
          "worker does not accept by pair-count shortcuts")

    separator = rust("separator.rs")
    check("total_weighted_loss" in separator or "weighted_loss" in separator,
          "separator carries weighted-loss state")
    check("min_by" in separator and "weighted" in separator.lower(),
          "separator best-worker selection is weighted-loss based")

    explore = rust("explore.rs")
    check("pool" in explore.lower() and "restore" in explore.lower(), "exploration has pool/restore logic")
    check("contained" in explore.lower(), "exploration has contained-item relocation")

    print(f"\nResult: PASS={PASS} FAIL={FAIL} WARN={WARN}")
    if FAIL:
        print("SGH-Q25-R3 smoke: FAIL")
        return 1
    print("SGH-Q25-R3 smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
