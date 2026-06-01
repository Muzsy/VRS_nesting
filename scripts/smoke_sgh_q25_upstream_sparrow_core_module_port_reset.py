#!/usr/bin/env python3
"""SGH-Q25 upstream Sparrow module-port reset smoke.

This smoke is intentionally structural. Q25 is not allowed to pass by merely
improving dense runtime metrics; it must demonstrate that the production native
Sparrow core has been split into upstream-mapped modules and that the known
Q24R9 proxy shortcuts are no longer production paths.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SP = ROOT / "rust" / "vrs_solver" / "src" / "optimizer" / "sparrow"
REPORT = ROOT / "codex" / "reports" / "egyedi_solver" / "sgh_q25_upstream_sparrow_core_module_port_reset.md"

PASS = 0
FAIL = 0
PARTIAL = 0


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def partial(cond: bool, msg: str) -> None:
    global PASS, PARTIAL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        PARTIAL += 1
        print(f"  [PARTIAL] {msg}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def strip_tests_and_comments(text: str) -> str:
    # Drop Rust tests and comments to reduce false positives.
    text = re.sub(r"(?s)#\[cfg\(test\)\].*", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    return text


def rust_sources() -> dict[Path, str]:
    if not SP.exists():
        return {}
    return {p: strip_tests_and_comments(read(p)) for p in sorted(SP.rglob("*.rs"))}


def grep_any(pattern: str, sources: dict[Path, str]) -> list[Path]:
    rx = re.compile(pattern)
    return [p for p, text in sources.items() if rx.search(text)]


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        cp = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return cp.returncode, cp.stdout[-4000:]
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "")[-4000:] if isinstance(e.stdout, str) else "timeout"


def main() -> int:
    print("SGH-Q25 upstream Sparrow module-port reset smoke")
    sources = rust_sources()
    check(bool(sources), "optimizer/sparrow Rust sources exist")

    required = [
        "mod.rs",
        "model.rs",
        "optimizer.rs",
        "lbf.rs",
        "worker.rs",
        "separator.rs",
        "explore.rs",
        "fixed_sheet.rs",
        "diagnostics.rs",
        "sample/mod.rs",
        "sample/search.rs",
        "sample/coord_descent.rs",
        "sample/best_samples.rs",
        "sample/uniform_sampler.rs",
        "eval/mod.rs",
        "eval/sample_eval.rs",
        "eval/sep_evaluator.rs",
        "eval/lbf_evaluator.rs",
        "eval/specialized_cde_pipeline.rs",
        "quantify/mod.rs",
        "quantify/tracker.rs",
        "quantify/pair_matrix.rs",
        "quantify/overlap_proxy.rs",
    ]
    for rel in required:
        check((SP / rel).exists(), f"required upstream-mapped module exists: {rel}")

    mod_rs = SP / "mod.rs"
    mod_lines = len(read(mod_rs).splitlines()) if mod_rs.exists() else 999999
    check(mod_lines <= 260, f"sparrow/mod.rs is thin wiring module (<=260 lines, got {mod_lines})")

    # No single file should remain a monolithic implementation. This is a soft-ish
    # structural bar; if exceeded, it should be intentionally split further.
    for p in sources:
        lines = len(read(p).splitlines())
        if p.name == "mod.rs" and p.parent == SP:
            continue
        check(lines <= 900, f"module is not an oversized monolith: {p.relative_to(ROOT)} ({lines} lines)")

    combined = "\n".join(sources.values())

    # Architecture preservation.
    check("SparrowProblem" in combined and "SparrowOptimizer" in combined and "SparrowSolution" in combined,
          "native SparrowProblem/SparrowOptimizer/SparrowSolution path remains present")
    for banned in ["WorkingLayout", "VrsCollisionTracker", "SparrowSeparationKernel", "PhaseOptimizer", "MultiSheetManager", "search_position_for_target", "build_constructive_seed_layout"]:
        offenders = grep_any(r"\b" + re.escape(banned) + r"\b", sources)
        check(not offenders, f"no production {banned} dependency in optimizer/sparrow")

    # Known Q24R9 shortcuts must be gone from production.
    banned_patterns = [
        (r"\bshelf_construct\b", "no shelf_construct LBF shortcut"),
        (r"\bfallback_anchor\b", "no fallback_anchor LBF shortcut"),
        (r"\baabb_penetration\s*\(", "no AABB penetration as evaluator/ranking loss"),
        (r"overlap_score\s*\+=", "no overlap_score proxy fallback"),
        (r"new_total\s*<\s*old_total", "no loose new_total worker acceptance"),
        (r"new_pairs\s*<\s*old_pairs", "no loose new_pairs worker acceptance"),
        (r"pair_count\s*\.\s*cmp\s*\(", "no pair-count-first worker comparator"),
        (r"lowest collision-pair count wins", "no documented pair-count-first comparator"),
    ]
    for pat, msg in banned_patterns:
        offenders = grep_any(pat, sources)
        check(not offenders, f"{msg}")

    # Exact upstream-module names should be meaningful, not just empty files.
    expected_tokens = {
        "quantify/tracker.rs": ["CollisionTracker", "weighted", "weight", "loss"],
        "quantify/pair_matrix.rs": ["Pair", "Matrix"],
        "eval/sep_evaluator.rs": ["SeparationEvaluator", "upper", "bound"],
        "eval/lbf_evaluator.rs": ["LBFEvaluator"],
        "eval/specialized_cde_pipeline.rs": ["Hazard", "Collector"],
        "sample/search.rs": ["search", "BestSamples"],
        "sample/coord_descent.rs": ["Coordinate", "Descent", "rotation"],
        "sample/best_samples.rs": ["BestSamples"],
        "sample/uniform_sampler.rs": ["Uniform"],
        "lbf.rs": ["LBF"],
        "worker.rs": ["Worker", "weighted"],
        "separator.rs": ["Separator", "worker", "weighted"],
        "explore.rs": ["explore", "restore", "disrupt"],
    }
    for rel, toks in expected_tokens.items():
        text = read(SP / rel)
        for tok in toks:
            check(tok.lower() in text.lower(), f"{rel} contains expected upstream concept token: {tok}")

    # Compression must remain absent from the core path.
    compression_refs = grep_any(r"compression|compress", sources)
    # Allow comments only already stripped; any production ref is suspicious.
    check(not compression_refs, "compression/compress not implemented or used in production optimizer/sparrow")

    # Report checks.
    rpt = read(REPORT)
    check(bool(rpt), "Q25 report exists")
    check("SGH-Q25_STATUS:" in rpt, "report contains SGH-Q25_STATUS")
    check("Upstream file | Upstream type/function | Local file | Local type/function | Status | Fixed-sheet deviation | Evidence" in rpt,
          "report contains required upstream-to-local mapping table header")
    for rel in [
        "optimizer/lbf.rs", "optimizer/worker.rs", "optimizer/separator.rs", "optimizer/explore.rs",
        "sample/search.rs", "sample/coord_descent.rs", "sample/best_samples.rs", "sample/uniform_sampler.rs",
        "eval/sep_evaluator.rs", "eval/lbf_evaluator.rs", "eval/sample_eval.rs", "eval/specialized_jaguars_pipeline.rs",
        "quantify/mod.rs", "quantify/tracker.rs", "quantify/pair_matrix.rs",
    ]:
        check(rel in rpt, f"report maps upstream {rel}")
    check("DEFERRED_COMPRESSION_ONLY" in rpt, "report explicitly defers compression-only upstream logic")
    check("ADAPTED_FIXED_SHEET" in rpt, "report documents fixed-sheet adaptations")

    vague_bad = ["Sparrow-like", "similar enough", "equivalent enough", "future work", "TODO"]
    for phrase in vague_bad:
        check(phrase.lower() not in rpt.lower(), f"report avoids vague escape phrase: {phrase}")

    # Try build/test if Rust is available; do not silently pass if cargo exists and fails.
    cargo_rc, cargo_out = run(["cargo", "--version"], timeout=20)
    if cargo_rc == 0:
        rc, out = run(["cargo", "build", "--manifest-path", "rust/vrs_solver/Cargo.toml", "--release"], timeout=300)
        check(rc == 0, "cargo build --release passes")
        if rc != 0:
            print(out)
        rc, out = run(["cargo", "test", "--manifest-path", "rust/vrs_solver/Cargo.toml", "--lib"], timeout=300)
        check(rc == 0, "cargo test --lib passes")
        if rc != 0:
            print(out)
    else:
        partial(False, "cargo unavailable in this environment; runtime build/test not executed by smoke")

    print(f"\nRESULT: pass={PASS} fail={FAIL} partial={PARTIAL}")
    if FAIL:
        return 1
    if PARTIAL:
        print("STATUS: PASS_WITH_ENV_PARTIAL")
        return 0
    print("STATUS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
