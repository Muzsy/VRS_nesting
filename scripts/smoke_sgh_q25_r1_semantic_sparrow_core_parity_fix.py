#!/usr/bin/env python3
"""SGH-Q25-R1 semantic Sparrow core parity smoke.

This smoke is intentionally stricter than Q25. Q25's structural module split is
not enough. This script rejects the specific stub/proxy patterns found by the
Q25 audit.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow"
REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q25_r1_semantic_sparrow_core_parity_fix.md"

PASS = 0
FAIL = 0
WARN = 0


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


def rust_file(rel: str) -> str:
    return strip_comments(read(SP / rel))


def all_rust() -> str:
    return "\n".join(strip_comments(read(p)) for p in SP.rglob("*.rs")) if SP.exists() else ""


def fn_body(text: str, name: str) -> str:
    m = re.search(rf"fn\s+{re.escape(name)}\s*\([^)]*\)\s*(?:->\s*[^{{]+)?\{{", text)
    if not m:
        return ""
    i = m.end()
    depth = 1
    j = i
    while j < len(text) and depth:
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
        j += 1
    return text[i:j-1]


def main() -> int:
    print("SGH-Q25-R1 semantic Sparrow core parity smoke")
    check(SP.exists(), "optimizer/sparrow module exists")

    required = [
        "eval/specialized_cde_pipeline.rs",
        "eval/sep_evaluator.rs",
        "eval/lbf_evaluator.rs",
        "quantify/mod.rs",
        "quantify/tracker.rs",
        "quantify/overlap_proxy.rs",
        "lbf.rs",
        "worker.rs",
        "separator.rs",
        "explore.rs",
        "sample/search.rs",
        "sample/coord_descent.rs",
    ]
    for rel in required:
        check((SP / rel).exists(), f"required semantic module exists: {rel}")

    specialized = rust_file("eval/specialized_cde_pipeline.rs")
    check("struct SpecializedCdeHazardCollector;" not in specialized,
          "SpecializedCdeHazardCollector is not an empty unit struct")
    reload = fn_body(specialized, "reload")
    check(bool(reload) and "loss_bound" in reload and len(reload.strip()) > 40,
          "SpecializedCdeHazardCollector::reload is stateful, not no-op")
    check(any(tok in specialized for tok in ["early_terminate", "loss_bound", "accumulated", "hazards", "pair"]),
          "specialized collector has hazard/loss/early-termination state")
    collect_body = fn_body(specialized, "collect_poly_collisions_in_detector_custom")
    check(bool(collect_body) and not re.fullmatch(r"\s*SpecializedCdeHazardCollector\s*", collect_body.strip() or ""),
          "collect_poly_collisions_in_detector_custom performs real collection, not empty return")

    sep = rust_file("eval/sep_evaluator.rs")
    banned_sep = [
        "hazard_extent_depth",
        "aabb_penetration",
        "ox.min(oy)",
        "ix * iy",
        "bbox extent",
    ]
    for b in banned_sep:
        check(b not in sep, f"SeparationEvaluator does not use banned proxy ranking: {b}")
    check("SpecializedCdeHazardCollector" in sep and "collect_poly_collisions_in_detector_custom" in sep,
          "SeparationEvaluator uses specialized CDE hazard collector")
    check("upper_bound" in sep and "reload" in sep and "early_terminate" in sep,
          "SeparationEvaluator has upper-bound reload/early-termination flow")

    quant = rust_file("quantify/mod.rs") + "\n" + rust_file("quantify/overlap_proxy.rs")
    check("overlap_area_proxy" in quant, "quantification uses upstream overlap_area_proxy")
    check("calc_shape_penalty" in quant or "shape_penalty" in quant,
          "quantification includes shape penalty")
    check("resolution_distance" not in quant.lower() and "probe_pair_resolution" not in all_rust().lower(),
          "resolution-distance quantification is not the default production quantifier")

    lbf = rust_file("lbf.rs")
    banned_lbf = [
        "fixed_sheet_recovery_candidate",
        "shelf_construct",
        "fallback_anchor",
        "candidate_penalty",
        "ix * iy",
        "overlap_score",
    ]
    for b in banned_lbf:
        check(b not in lbf, f"LBF has no banned proxy/recovery path: {b}")
    check("search_placement" in lbf and "LBFEvaluator" in lbf,
          "LBF placement goes through search_placement + LBFEvaluator")

    sepmod = rust_file("separator.rs")
    check("weighted_loss" in sepmod or "total_weighted_loss" in sepmod,
          "separator uses weighted loss terminology")
    check(not re.search(r"colliding_pairs\s*\(\).*<.*best", sepmod),
          "separator best-worker selection is not pair-count-first")
    check("min_by" in sepmod and "weighted" in sepmod.lower(),
          "best worker selection is based on weighted loss")

    worker = rust_file("worker.rs")
    check("weighted" in worker.lower() and "old" in worker.lower() and "new" in worker.lower(),
          "worker move acceptance compares weighted loss before/after")
    check("new_pairs" not in worker,
          "worker does not accept moves via new_pairs fallback")

    explore = rust_file("explore.rs")
    check("practically_contained" in explore or "contained" in explore.lower(),
          "exploration has contained-item relocation equivalent")
    check("convert" in explore.lower() or "transform" in explore.lower(),
          "contained-item relocation transforms/clamps moved items")

    allsrc = all_rust()
    check("WorkingLayout" not in allsrc and "VrsCollisionTracker" not in allsrc,
          "production optimizer/sparrow sources do not use old VRS core model")
    check("compression_phase" not in allsrc and "compression_pass" not in allsrc,
          "compression remains excluded from optimizer/sparrow production source")

    report = read(REPORT)
    warn(bool(report), "Q25-R1 report exists")
    if report:
        check("SGH-Q25-R1_STATUS:" in report, "report contains explicit status marker")
        check("Upstream file | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence" in report,
              "report contains required semantic mapping table")
        check("Sparrow-like" not in report and "future work" not in report.lower(),
              "report does not use vague pass language")

    print(f"\nResult: PASS={PASS} FAIL={FAIL} WARN={WARN}")
    if FAIL:
        print("SGH-Q25-R1 smoke: FAIL")
        return 1
    print("SGH-Q25-R1 smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
