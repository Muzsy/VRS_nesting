#!/usr/bin/env python3
"""SGH-Q43b — Smoke validator for the own vrs_solver 1500x6000 baseline run.

Validates the presence and structural integrity of the Q43b artifacts, the
own-solver-code immutability diff, and the required report sections. Mirrors
scripts/smoke_sgh_q43_upstream_sparrow_strip_audit.py for the Q43b case.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q43B = ROOT / "artifacts" / "benchmarks" / "sgh_q43b"
REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q43b_own_vrs_solver_1500x6000_baseline.md"


def exists_nonempty(p: Path) -> bool:
    return p.exists() and p.stat().st_size > 0


def exists_any_size(p: Path) -> bool:
    return p.exists()


def main() -> int:
    errors: list[str] = []

    # 1) Required artifacts (diff logs are special — they SHOULD be empty)
    for p, label in [
        (Q43B / "upstream_clone_info.json", "upstream_clone_info.json"),
        (Q43B / "upstream_build.log", "upstream_build.log"),
        (Q43B / "upstream_summary.json", "upstream_summary.json"),
        (Q43B / "q43b_summary.json", "q43b_summary.json"),
        (Q43B / "comparison_summary.json", "comparison_summary.json"),
        (Q43B / "semantic_parity_matrix.json", "semantic_parity_matrix.json"),
        (Q43B / "pre_own_source_status.log", "pre_own_source_status.log"),
        (Q43B / "pre_own_source_diff.log", "pre_own_source_diff.log"),
        (Q43B / "post_own_source_status.log", "post_own_source_status.log"),
        (Q43B / "post_own_source_diff.log", "post_own_source_diff.log"),
        (Q43B / "upstream_run_1200.log", "upstream_run_1200.log"),
    ]:
        if p.name in ("pre_own_source_diff.log", "post_own_source_diff.log"):
            if not exists_any_size(p):
                errors.append(f"missing immutability proof file: {label} ({p})")
        else:
            if not exists_nonempty(p):
                errors.append(f"missing or empty artifact: {label} ({p})")

    # 2) Runner + smoke scripts present
    for p, label in [
        (ROOT / "scripts" / "bench_sgh_q43b_own_full276_1500x6000.py", "runner script"),
        (ROOT / "scripts" / "build_sgh_q43b_comparison_artifacts.py", "comparison builder"),
        (Path(__file__), "smoke script (self)"),
    ]:
        if not exists_nonempty(p):
            errors.append(f"missing script: {label} ({p})")

    # 3) JSON parse checks
    for p, label in [
        (Q43B / "upstream_clone_info.json", "upstream_clone_info.json"),
        (Q43B / "upstream_summary.json", "upstream_summary.json"),
        (Q43B / "q43b_summary.json", "q43b_summary.json"),
        (Q43B / "comparison_summary.json", "comparison_summary.json"),
        (Q43B / "semantic_parity_matrix.json", "semantic_parity_matrix.json"),
    ]:
        if p.exists():
            try:
                json.loads(p.read_text())
            except Exception as e:
                errors.append(f"{label} not valid JSON: {e}")

    # 4) Own source immutability: pre + post diff must be empty
    for p, label in [
        (Q43B / "pre_own_source_diff.log", "pre_own_source_diff.log"),
        (Q43B / "post_own_source_diff.log", "post_own_source_diff.log"),
    ]:
        if not p.exists():
            errors.append(f"{label} missing (own source immutability proof absent)")
        elif p.stat().st_size > 0:
            errors.append(f"{label} is not empty: own solver source must not change")

    # 5) Report presence and required sections
    if not exists_nonempty(REPORT):
        errors.append(f"missing report: {REPORT}")
    else:
        text = REPORT.read_text()
        required = [
            "1500x6000",
            "vrs_solver",
            "Own solver code immutability proof",
            "Semantic parity audit methodology",
            "Q43 upstream Sparrow SPP 1500x6000",
            "Q43b own vrs_solver 1x1500x6000",
            "Q42 own vrs_solver 3x1500x3000",
            "Direct comparability",
            "Final verdict",
            "MATCH",
            "INTENTIONAL DIVERGENCE",
            "PARTIAL_DIRECTLY_COMPARABLE",
        ]
        for needle in required:
            if needle not in text:
                errors.append(f"report missing required section/phrase: {needle!r}")

    # 6) upstream_clone_info has the required fields
    clone_info = Q43B / "upstream_clone_info.json"
    if clone_info.exists():
        try:
            ci = json.loads(clone_info.read_text())
            for field in ("solver_binary_path", "solver_commit_hash", "solver_build_command"):
                if not ci.get(field):
                    errors.append(f"upstream_clone_info.json missing field: {field}")
        except Exception:
            pass

    # 7) semantic_parity_matrix has 9 topics with valid verdicts
    pm = Q43B / "semantic_parity_matrix.json"
    if pm.exists():
        try:
            pmd = json.loads(pm.read_text())
            topics = pmd.get("topics", [])
            if len(topics) < 9:
                errors.append(f"semantic_parity_matrix.json: expected >=9 topics, got {len(topics)}")
            allowed_verdicts = {
                "MATCH", "ADAPTED MATCH", "INTENTIONAL DIVERGENCE",
                "RISKY DIVERGENCE", "UNKNOWN / NOT VERIFIED",
            }
            for t in topics:
                v = t.get("verdict")
                if v not in allowed_verdicts:
                    errors.append(f"semantic_parity_matrix.json topic '{t.get('id','?')}' verdict '{v}' not in allowed set")
        except Exception as e:
            errors.append(f"semantic_parity_matrix.json not parseable: {e}")

    if errors:
        print("SGH-Q43b smoke: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SGH-Q43b smoke: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
