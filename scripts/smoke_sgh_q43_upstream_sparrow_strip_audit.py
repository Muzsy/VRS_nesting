#!/usr/bin/env python3
"""SGH-Q43 — Smoke validator for the upstream Sparrow strip baseline + parity audit.

Validates the presence and structural integrity of the Q43 artifacts, the
own-solver-code immutability diff, and the required report sections.
Does NOT execute upstream; that is the runner's job.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Q43 = ROOT / "artifacts" / "benchmarks" / "sgh_q43"
UPSTREAM = Q43 / "upstream"
REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit.md"
TILDE_PATHS = ["rust/vrs_solver/src", "api", "worker", "frontend", "vrs_nesting"]


def exists_nonempty(p: Path) -> bool:
    return p.exists() and p.stat().st_size > 0


def exists_any_size(p: Path) -> bool:
    """File exists (may be 0 bytes; used for diff-log files whose emptiness IS the proof)."""
    return p.exists()


def check_artifact(path: Path, label: str, errors: list[str]) -> None:
    if not exists_nonempty(path):
        errors.append(f"missing or empty artifact: {label} ({path})")


def check_report_sections(report_text: str, required: list[str], errors: list[str]) -> None:
    for needle in required:
        if needle not in report_text:
            errors.append(f"report missing required section/phrase: {needle!r}")


def main() -> int:
    errors: list[str] = []

    # 1) Required artifacts (diff logs are special — they SHOULD be empty)
    for p, label in [
        (Q43 / "upstream_clone_info.json", "upstream_clone_info.json"),
        (Q43 / "upstream_build.log", "upstream_build.log"),
        (Q43 / "upstream_summary.json", "upstream_summary.json"),
        (Q43 / "comparison_summary.json", "comparison_summary.json"),
        (Q43 / "semantic_parity_matrix.json", "semantic_parity_matrix.json"),
        (Q43 / "pre_own_source_status.log", "pre_own_source_status.log"),
        (Q43 / "pre_own_source_diff.log", "pre_own_source_diff.log"),
        (Q43 / "post_own_source_status.log", "post_own_source_status.log"),
        (Q43 / "post_own_source_diff.log", "post_own_source_diff.log"),
    ]:
        if p.name in ("pre_own_source_diff.log", "post_own_source_diff.log"):
            if not exists_any_size(p):
                errors.append(f"missing immutability proof file: {label} ({p})")
        else:
            check_artifact(p, label, errors)

    # 2) Runner + smoke scripts present
    for p, label in [
        (ROOT / "scripts" / "run_sgh_q43_upstream_sparrow_strip1500x6000.py", "runner script"),
        (Path(__file__), "smoke script (self)"),
    ]:
        check_artifact(p, label, errors)

    # 3) Upstream run logs — at least Run A, Run B if it was executed
    summary_path = Q43 / "upstream_summary.json"
    run_a_log = Q43 / "upstream_run_1200.log"
    run_b_log = Q43 / "upstream_run_2400.log"
    if not exists_nonempty(run_a_log):
        errors.append(f"missing or empty: upstream_run_1200.log")
    if summary_path.exists():
        try:
            s = json.loads(summary_path.read_text())
            rb = s.get("run_b", {})
            rb_status = rb.get("status")
            # Run B is "expected to be present" only if it completed (status==ok or error).
            # status=pending means Run B is still running; status=skipped means it was not required.
            if rb_status not in (None, "skipped", "pending"):
                if not exists_nonempty(run_b_log):
                    errors.append("run_b completed but upstream_run_2400.log is missing/empty")
        except Exception as e:
            errors.append(f"could not parse upstream_summary.json: {e}")

    # 4) Upstream inputs
    in_a = UPSTREAM / "inputs" / "sgh_q43_upstream_full276_1500x6000_continuous_1200.json"
    if not exists_nonempty(in_a):
        errors.append(f"missing upstream Run A input: {in_a}")

    # 5) Upstream output for Run A
    out_a = UPSTREAM / "run_1200" / "output" / f"final_sgh_q43_upstream_full276_1500x6000_continuous_1200.json"
    if not exists_nonempty(out_a):
        errors.append(f"missing upstream Run A output: {out_a}")

    # 6) JSON parse checks
    for p, label in [
        (Q43 / "upstream_clone_info.json", "upstream_clone_info.json"),
        (Q43 / "upstream_summary.json", "upstream_summary.json"),
        (Q43 / "comparison_summary.json", "comparison_summary.json"),
        (Q43 / "semantic_parity_matrix.json", "semantic_parity_matrix.json"),
    ]:
        if p.exists():
            try:
                json.loads(p.read_text())
            except Exception as e:
                errors.append(f"{label} not valid JSON: {e}")

    # 7) Own source immutability: pre + post diff must be empty (size == 0)
    for p, label in [
        (Q43 / "pre_own_source_diff.log", "pre_own_source_diff.log"),
        (Q43 / "post_own_source_diff.log", "post_own_source_diff.log"),
    ]:
        if not p.exists():
            errors.append(f"{label} missing (own source immutability proof absent)")
        elif p.stat().st_size > 0:
            errors.append(f"{label} is not empty: own solver source must not change")

    # 8) Report presence and required sections
    if not exists_nonempty(REPORT):
        errors.append(f"missing report: {REPORT}")
    else:
        text = REPORT.read_text()
        required = [
            "1500x6000",
            "runtime",
            "Own solver code immutability proof",
            "Semantic parity audit methodology",
            "Strip vs finite-stock multisheet divergence",
            "Margin / spacing / kerf parity",
            "Final verdict",
            "MATCH",
            "INTENTIONAL DIVERGENCE",
            "NOT DIRECTLY COMPARABLE",
        ]
        check_report_sections(text, required, errors)

    # 9) upstream_clone_info has commit hash
    clone_info = Q43 / "upstream_clone_info.json"
    if clone_info.exists():
        try:
            ci = json.loads(clone_info.read_text())
            if not ci.get("upstream_commit_hash") or ci["upstream_commit_hash"] == "unknown":
                errors.append("upstream_clone_info.json: upstream_commit_hash missing or 'unknown'")
        except Exception:
            pass

    # 10) semantic_parity_matrix has the 9 audit topics with verdicts
    pm = Q43 / "semantic_parity_matrix.json"
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
        print("SGH-Q43 smoke: FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("SGH-Q43 smoke: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
