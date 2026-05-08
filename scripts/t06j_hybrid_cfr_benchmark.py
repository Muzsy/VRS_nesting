#!/usr/bin/env python3
"""
T06j — Quality-preserving CFR reduction benchmark.

Runs two passes on the LV8 benchmark via shell pipe (cat file | binary):
  A) Baseline: no HYBRID_CFR — full CFR union on all placements
  B) Hybrid:   NESTING_ENGINE_HYBRID_CFR=1 — fast-path candidate gen below threshold

Reports quality gates (placed_count, sheet_count, utilization) and
performance metrics (CFR call count, union time, total runtime).

Usage:
  python3 scripts/t06j_hybrid_cfr_benchmark.py [--timeout 300] [--threshold 50]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_PATH = REPO_ROOT / "rust/nesting_engine/target/release/nesting_engine"
FIXTURE_PATH = REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json"

# LV8 sheet dimensions (from fixture, in mm)
LV8_SHEET_WIDTH_MM = 1500.0
LV8_SHEET_HEIGHT_MM = 3000.0
LV8_SHEET_AREA_MM2 = LV8_SHEET_WIDTH_MM * LV8_SHEET_HEIGHT_MM


@dataclass
class RunResult:
    """Parsed result from a single nesting_engine run."""
    mode: str
    placed_count: int = 0
    sheet_count: int = 0
    unplaced_count: int = 0
    utilization_pct: float = 0.0
    status: str = "unknown"
    runtime_sec: float = 0.0
    cfr_calls: int = 0
    cfr_union_ms_total: float = 0.0
    cfr_diff_ms_total: float = 0.0
    hybrid_calls: int = 0  # Number of placements using hybrid path
    cfr_diag_lines: list[dict] = field(default_factory=list)
    raw_stderr: str = ""
    raw_stdout: str = ""
    timed_out: bool = False


def parse_cfr_diag_line(line: str) -> Optional[dict]:
    """Parse a CFR_DIAG_V1 log line."""
    if not line.startswith("CFR_DIAG_V1"):
        return None
    try:
        parts = line.split()
        data = {}
        for part in parts[1:]:
            if "=" in part:
                key, val = part.split("=", 1)
                try:
                    data[key] = float(val) if "." in val else int(val)
                except ValueError:
                    data[key] = val
        return data
    except Exception:
        return None


def run_nesting_shell_pipe(
    mode: str,
    extra_env: dict[str, str],
    timeout_sec: int,
    extra_args: list[str] | None = None,
) -> RunResult:
    """Run nesting_engine with given mode via shell pipe (cat file | binary)."""
    env = {
        "NESTING_ENGINE_NFP_KERNEL": "cgal_reference",
        "NESTING_ENGINE_STOP_MODE": "work_budget",
        "NESTING_ENGINE_NFP_RUNTIME_DIAG": "1",
        "NFP_ENABLE_CGAL_REFERENCE": "1",
        "NFP_CGAL_PROBE_BIN": str(REPO_ROOT / "tools/nfp_cgal_probe/build/nfp_cgal_probe"),
    }
    env.update(extra_env)

    cmd = [
        str(BIN_PATH),
        "nest",
        "--placer", "nfp",
        "--nfp-kernel", "cgal_reference",
        "--search", "sa",
        "--compaction", "slide",
    ]
    if extra_args:
        cmd.extend(extra_args)

    # Use shell pipe: cat file | binary (reliable for stdin)
    shell_cmd = f"cat '{FIXTURE_PATH}' | {' '.join(cmd)}"

    start = time.monotonic()
    try:
        proc = subprocess.run(
            shell_cmd,
            env=env,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        result = RunResult(mode=mode, runtime_sec=elapsed, status="timeout", timed_out=True)
        result.raw_stderr = f"Process timed out after {timeout_sec}s"
        return result

    elapsed = time.monotonic() - start
    stderr = proc.stderr
    stdout = proc.stdout

    result = RunResult(mode=mode, runtime_sec=elapsed, raw_stderr=stderr, raw_stdout=stdout)

    # Parse JSON output from stdout
    # The binary outputs JSON to stdout (without newlines), so we need to extract it
    for line in stdout.split("\n"):
        if line.strip().startswith("{"):
            try:
                data = json.loads(line.strip())
                if "placements" in data or "placement_result" in data:
                    result.placed_count = int(data.get("placed_count", data.get("placements", []).__len__() or 0))
                    result.sheet_count = int(data.get("sheets_used", data.get("sheets", [0]).__len__() if isinstance(data.get("sheets"), list) else 0))
                    result.status = str(data.get("status", "unknown"))
                    result.utilization_pct = float(data.get("utilization_pct", data.get("objective", {}).get("utilization_pct", 0)))
                    break
            except (json.JSONDecodeError, TypeError):
                continue

    # Extract placed_count and sheets_used from output text
    placed_m = re.search(r'"placed_count"\s*:\s*(\d+)', stdout)
    sheets_m = re.search(r'"sheets_used"\s*:\s*(\d+)', stdout)
    util_m = re.search(r'"utilization_pct"\s*:\s*([0-9.]+)', stdout)
    status_m = re.search(r'"status"\s*:\s*"([^"]+)"', stdout)

    if placed_m:
        result.placed_count = int(placed_m.group(1))
    if sheets_m:
        result.sheet_count = int(sheets_m.group(1))
    if util_m:
        result.utilization_pct = float(util_m.group(1))
    if status_m:
        result.status = status_m.group(1)

    # Parse NFP_RUNTIME_DIAG_V1 for aggregate stats
    runtime_diag_m = re.search(
        r'NFP_RUNTIME_DIAG_V1[^"]*cfr_calls=(\d+)[^"]*cfr_union_ms_total=([0-9.]+)[^"]*cfr_diff_ms_total=([0-9.]+)',
        stderr
    )
    if runtime_diag_m:
        result.cfr_calls = int(runtime_diag_m.group(1))
        result.cfr_union_ms_total = float(runtime_diag_m.group(2))
        result.cfr_diff_ms_total = float(runtime_diag_m.group(3))

    # Parse HYBRID_CFR diagnostics
    result.hybrid_calls = stderr.count("HYBRID_CFR] nfp_polys=")

    # Parse CFR_DIAG_V1 lines for detailed breakdown
    for line in stderr.split("\n"):
        diag = parse_cfr_diag_line(line)
        if diag:
            result.cfr_diag_lines.append(diag)

    # Count actual CFR calls
    cfr_diag_count = stderr.count("[CFR DIAG] START")
    if result.cfr_calls == 0 and cfr_diag_count > 0:
        result.cfr_calls = cfr_diag_count

    return result


def summarize_diag(diag_lines: list[dict]) -> dict[str, Any]:
    """Summarize CFR_DIAG_V1 statistics."""
    if not diag_lines:
        return {}

    nfp_counts = [d.get("nfp_poly_count", 0) for d in diag_lines]
    union_times = [d.get("union_time_ms", 0.0) for d in diag_lines]
    diff_times = [d.get("diff_time_ms", 0.0) for d in diag_lines]
    total_times = [d.get("total_cfr_time_ms", 0.0) for d in diag_lines]
    components_list = [d.get("component_count", 0) for d in diag_lines]
    candidates_list = [d.get("candidate_count", 0) for d in diag_lines]

    return {
        "total_cfr_calls": len(diag_lines),
        "nfp_poly_avg": sum(nfp_counts) / len(nfp_counts) if nfp_counts else 0,
        "nfp_poly_max": max(nfp_counts) if nfp_counts else 0,
        "nfp_poly_min": min(nfp_counts) if nfp_counts else 0,
        "union_ms_avg": sum(union_times) / len(union_times) if union_times else 0,
        "union_ms_total": sum(union_times),
        "diff_ms_avg": sum(diff_times) / len(diff_times) if diff_times else 0,
        "diff_ms_total": sum(diff_times),
        "total_ms_total": sum(total_times),
        "components_avg": sum(components_list) / len(components_list) if components_list else 0,
        "candidates_avg": sum(candidates_list) / len(candidates_list) if candidates_list else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="T06j hybrid CFR benchmark")
    parser.add_argument("--timeout", type=int, default=300, help="Per-run timeout in seconds")
    parser.add_argument("--threshold", type=int, default=50, help="HYBRID_NFP_COUNT_THRESHOLD")
    parser.add_argument("--sa-iters", type=int, default=1, help="Number of SA iterations")
    parser.add_argument("--sa-eval-budget-sec", type=int, default=10, help="SA eval budget in seconds")
    parser.add_argument("--skip-baseline", action="store_true", help="Skip baseline run")
    parser.add_argument("--skip-hybrid", action="store_true", help="Skip hybrid run")
    args = parser.parse_args()

    extra_args = ["--sa-iters", str(args.sa_iters), "--sa-eval-budget-sec", str(args.sa_eval_budget_sec)]

    print("=" * 70)
    print("T06j — Quality-preserving CFR Reduction Benchmark")
    print("=" * 70)
    print(f"Fixture: {FIXTURE_PATH}")
    print(f"Binary:  {BIN_PATH}")
    print(f"Timeout: {args.timeout}s per run")
    print(f"SA iters: {args.sa_iters}, eval_budget: {args.sa_eval_budget_sec}s")
    print(f"Hybrid threshold: {args.threshold}")
    print()

    results = {}

    # Run A: Baseline (no HYBRID_CFR)
    if not args.skip_baseline:
        print("[Baseline] Running full CFR path (no HYBRID_CFR)...")
        baseline = run_nesting_shell_pipe(
            mode="baseline",
            extra_env={},
            timeout_sec=args.timeout,
            extra_args=extra_args,
        )
        results["baseline"] = baseline
        print(f"  placed={baseline.placed_count} sheets={baseline.sheet_count} "
              f"utilization={baseline.utilization_pct:.2f}% "
              f"status={baseline.status} runtime={baseline.runtime_sec:.1f}s")
        print(f"  cfr_calls={baseline.cfr_calls} cfr_union_ms={baseline.cfr_union_ms_total:.1f}")
        print()

    # Run B: Hybrid mode
    if not args.skip_hybrid:
        print(f"[Hybrid] Running with NESTING_ENGINE_HYBRID_CFR=1 (threshold={args.threshold})...")
        hybrid = run_nesting_shell_pipe(
            mode="hybrid",
            extra_env={
                "NESTING_ENGINE_HYBRID_CFR": "1",
                "NESTING_ENGINE_HYBRID_CFR_DIAG": "1",
            },
            timeout_sec=args.timeout,
            extra_args=extra_args,
        )
        results["hybrid"] = hybrid
        print(f"  placed={hybrid.placed_count} sheets={hybrid.sheet_count} "
              f"utilization={hybrid.utilization_pct:.2f}% "
              f"status={hybrid.status} runtime={hybrid.runtime_sec:.1f}s")
        print(f"  cfr_calls={hybrid.cfr_calls} cfr_union_ms={hybrid.cfr_union_ms_total:.1f}")
        print(f"  hybrid_path_calls={hybrid.hybrid_calls}")
        print()

    # Print quality gate comparison
    print("=" * 70)
    print("QUALITY GATE COMPARISON")
    print("=" * 70)

    if "baseline" in results and "hybrid" in results:
        b = results["baseline"]
        h = results["hybrid"]

        print(f"{'Metric':<30} {'Baseline':>12} {'Hybrid':>12} {'Delta':>12}")
        print("-" * 70)
        print(f"{'placed_count':<30} {b.placed_count:>12} {h.placed_count:>12} {h.placed_count - b.placed_count:>+12}")
        print(f"{'sheet_count':<30} {b.sheet_count:>12} {h.sheet_count:>12} {h.sheet_count - b.sheet_count:>+12}")
        print(f"{'utilization_pct':<30} {b.utilization_pct:>12.2f} {h.utilization_pct:>12.2f} {h.utilization_pct - b.utilization_pct:>+12.2f}")
        print(f"{'cfr_calls':<30} {b.cfr_calls:>12} {h.cfr_calls:>12} {h.cfr_calls - b.cfr_calls:>+12}")
        print(f"{'cfr_union_ms_total':<30} {b.cfr_union_ms_total:>12.1f} {h.cfr_union_ms_total:>12.1f} {h.cfr_union_ms_total - b.cfr_union_ms_total:>+12.1f}")
        print(f"{'cfr_diff_ms_total':<30} {b.cfr_diff_ms_total:>12.1f} {h.cfr_diff_ms_total:>12.1f} {h.cfr_diff_ms_total - b.cfr_diff_ms_total:>+12.1f}")
        print(f"{'runtime_sec':<30} {b.runtime_sec:>12.1f} {h.runtime_sec:>12.1f} {h.runtime_sec - b.runtime_sec:>+12.1f}")
        print(f"{'hybrid_path_calls':<30} {'N/A':>12} {h.hybrid_calls:>12}")
        print()

        # Quality verdict
        placed_delta = h.placed_count - b.placed_count
        sheet_delta = h.sheet_count - b.sheet_count

        quality_pass = True
        issues = []

        if placed_delta < 0:
            quality_pass = False
            issues.append(f"REGRESSION: placed_count dropped by {abs(placed_delta)}")
        elif placed_delta > 0:
            print(f"  NOTE: Hybrid placed {placed_delta} MORE parts than baseline")

        if sheet_delta > 0:
            quality_pass = False
            issues.append(f"REGRESSION: sheet_count increased by {sheet_delta} (less efficient)")
        elif sheet_delta < 0:
            print(f"  NOTE: Hybrid used {abs(sheet_delta)} FEWER sheets (more efficient)")

        print("=" * 70)
        if quality_pass and placed_delta == 0 and sheet_delta == 0:
            print("QUALITY VERDICT: PASS — hybrid matches baseline quality")
            print(f"  placed_count: {b.placed_count} == {h.placed_count} (no regression)")
            print(f"  sheet_count:  {b.sheet_count} == {h.sheet_count} (no regression)")
        elif quality_pass:
            print("QUALITY VERDICT: CONDITIONAL PASS")
            for issue in issues:
                print(f"  WARNING: {issue}")
        else:
            print("QUALITY VERDICT: FAIL — quality regression detected")
            for issue in issues:
                print(f"  FAIL: {issue}")

        print()

        # Performance analysis
        print("=" * 70)
        print("PERFORMANCE ANALYSIS")
        print("=" * 70)
        if b.cfr_union_ms_total > 0:
            union_saved = b.cfr_union_ms_total - h.cfr_union_ms_total
            union_pct_saved = (union_saved / b.cfr_union_ms_total) * 100.0
            print(f"CFR union time saved:  {union_saved:.1f}ms ({union_pct_saved:.1f}%)")
        if b.cfr_diff_ms_total > 0:
            diff_saved = b.cfr_diff_ms_total - h.cfr_diff_ms_total
            diff_pct_saved = (diff_saved / b.cfr_diff_ms_total) * 100.0
            print(f"CFR diff time saved:   {diff_saved:.1f}ms ({diff_pct_saved:.1f}%)")

        if h.hybrid_calls > 0 and b.cfr_calls > 0:
            pct = h.hybrid_calls / b.cfr_calls * 100.0
            print(f"Hybrid path calls:    {h.hybrid_calls} / {b.cfr_calls} = {pct:.1f}% of placements")

        if b.runtime_sec > 0 and h.runtime_sec > 0:
            runtime_saved = b.runtime_sec - h.runtime_sec
            print(f"Runtime saved:         {runtime_saved:.1f}s ({(runtime_saved/b.runtime_sec)*100:.1f}%)")

        print()

        # CFR_DIAG summary
        if b.cfr_diag_lines:
            print("=" * 70)
            print("BASELINE CFR_DIAG Summary (top 10 by union_time_ms)")
            print("=" * 70)
            diag_sorted = sorted(b.cfr_diag_lines, key=lambda d: d.get("union_time_ms", 0), reverse=True)[:10]
            print(f"{'nfp_poly':>8} {'union_ms':>10} {'diff_ms':>10} {'total_ms':>10} {'components':>10} {'candidates':>10}")
            print("-" * 70)
            for d in diag_sorted:
                print(f"{d.get('nfp_poly_count', 0):>8} "
                      f"{d.get('union_time_ms', 0):>10.2f} "
                      f"{d.get('diff_time_ms', 0):>10.2f} "
                      f"{d.get('total_cfr_time_ms', 0):>10.2f} "
                      f"{d.get('component_count', 0):>10} "
                      f"{d.get('candidate_count', 0):>10}")

            summary = summarize_diag(b.cfr_diag_lines)
            print()
            print("CFR_DIAG aggregate:")
            for k, v in summary.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.2f}")
                else:
                    print(f"  {k}: {v}")
            print()

        if h.cfr_diag_lines:
            print("=" * 70)
            print("HYBRID CFR_DIAG Summary (top 10 by union_time_ms)")
            print("=" * 70)
            diag_sorted = sorted(h.cfr_diag_lines, key=lambda d: d.get("union_time_ms", 0), reverse=True)[:10]
            print(f"{'nfp_poly':>8} {'union_ms':>10} {'diff_ms':>10} {'total_ms':>10} {'components':>10} {'candidates':>10}")
            print("-" * 70)
            for d in diag_sorted:
                print(f"{d.get('nfp_poly_count', 0):>8} "
                      f"{d.get('union_time_ms', 0):>10.2f} "
                      f"{d.get('diff_time_ms', 0):>10.2f} "
                      f"{d.get('total_cfr_time_ms', 0):>10.2f} "
                      f"{d.get('component_count', 0):>10} "
                      f"{d.get('candidate_count', 0):>10}")
            print()

            summary_h = summarize_diag(h.cfr_diag_lines)
            print("Hybrid CFR_DIAG aggregate:")
            for k, v in summary_h.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:.2f}")
                else:
                    print(f"  {k}: {v}")
            print()

    elif "baseline" in results:
        b = results["baseline"]
        print("BASELINE ONLY (hybrid skipped)")
        print(f"  placed_count:    {b.placed_count}")
        print(f"  sheet_count:     {b.sheet_count}")
        print(f"  utilization_pct: {b.utilization_pct:.2f}")
        print(f"  cfr_calls:       {b.cfr_calls}")
        print(f"  runtime:         {b.runtime_sec:.1f}s")
    elif "hybrid" in results:
        h = results["hybrid"]
        print("HYBRID ONLY (baseline skipped)")
        print(f"  placed_count:    {h.placed_count}")
        print(f"  sheet_count:     {h.sheet_count}")
        print(f"  cfr_calls:       {h.cfr_calls}")
        print(f"  hybrid_calls:   {h.hybrid_calls}")
        print(f"  runtime:         {h.runtime_sec:.1f}s")

    print()
    print("=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()