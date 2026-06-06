#!/usr/bin/env python3
"""SGH-Q29 Phase B — local CDE/search hotspot profiler runner.

Runs the local vrs_solver with SGH_Q29_CDE_PROFILE=1 on medium, lv8_subset and
dense191 cases, and produces a structured JSON summary + markdown report with
the cost breakdown.

This script ONLY measures — it does not optimize, tune, or modify the solver.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
ART_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q29"

SUMMARY_FILE = ART_DIR / "local_cde_hotspot_summary.json"
REPORT_FILE = ART_DIR / "local_cde_hotspot_report.md"

FIXTURES_DIR = ROOT / "rust" / "vrs_solver" / "tests" / "fixtures"
DENSE191_FIXTURE = FIXTURES_DIR / "sgh_q28_dense191_benchmark" / "dense_191_lv8_derived.json"

# Shared "medium" geometry: jakobs2 converted from SPP to local format (25 instances)
UPSTREAM_INPUT_DIR = ROOT / ".cache" / "sparrow" / "data" / "input"


# ── converter ────────────────────────────────────────────────────────────────

def _spp_to_local_input(
    spp_path: Path, time_secs: int, seed: int, case_id: str,
    sheet_w_factor: float = 3.0
) -> dict[str, Any]:
    spp = json.loads(spp_path.read_text())
    strip_h = spp["strip_height"]
    parts = []
    for item in spp["items"]:
        pts = item["shape"]["data"]
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if w < 1e-9 or h < 1e-9:
            continue
        min_x, min_y = min(xs), min(ys)
        pts_norm = [[round(x - min_x, 6), round(y - min_y, 6)] for x, y in pts]
        rots = [int(r) for r in item.get("allowed_orientations", [0.0])
                if abs(r - round(r)) < 1e-6]
        parts.append({
            "id": str(item["id"]),
            "width": round(w, 6),
            "height": round(h, 6),
            "quantity": item.get("demand", 1),
            "allowed_rotations_deg": rots or [0],
            "outer_points": pts_norm,
        })
    return {
        "contract_version": "v1",
        "project_name": f"sgh_q29_profile_{case_id}",
        "seed": seed,
        "time_limit_s": time_secs,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "margin_mm": 0.0,
        "stocks": [{"id": "S", "quantity": 1,
                    "width": strip_h * sheet_w_factor, "height": strip_h}],
        "parts": parts,
    }


def _lv8_input(subset_parts: list[dict], stocks: list[dict], time_secs: int, seed: int, case_id: str) -> dict:
    return {
        "contract_version": "v1",
        "project_name": f"sgh_q29_profile_{case_id}",
        "seed": seed,
        "time_limit_s": time_secs,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "margin_mm": 0.0,
        "stocks": stocks,
        "parts": subset_parts,
    }


# ── run local solver ──────────────────────────────────────────────────────────

def _run_local_profiled(solver_input: dict) -> dict[str, Any]:
    """Run local solver with SGH_Q29_CDE_PROFILE=1; extract profiling fields."""
    if not LOCAL_BIN.exists():
        return {"status": "error", "error": f"binary not found: {LOCAL_BIN}"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fi:
        json.dump(solver_input, fi)
        in_path = fi.name
    out_path = in_path.replace(".json", "_out.json")
    env = dict(os.environ)
    env["SGH_Q29_CDE_PROFILE"] = "1"
    t0 = time.time()
    try:
        r = subprocess.run(
            [str(LOCAL_BIN), "--input", in_path, "--output", out_path],
            capture_output=True, text=True,
            timeout=solver_input.get("time_limit_s", 60) + 90,
            env=env,
        )
        elapsed_ms = (time.time() - t0) * 1000
        if r.returncode != 0:
            return {"status": "error", "error": r.stderr[:300], "runtime_ms": elapsed_ms}
        out_data = json.loads(Path(out_path).read_text())
        od = out_data.get("optimizer_diagnostics") or {}
        placements = out_data.get("placements") or []
        return {
            "status": out_data.get("status", "ok"),
            "runtime_ms": round(elapsed_ms, 1),
            "placed_count": len(placements),
            "final_pairs": od.get("sparrow_collision_graph_final_pairs"),
            "iterations": od.get("sparrow_iterations"),
            "search_calls": od.get("sparrow_search_position_calls"),
            "search_samples": od.get("sparrow_search_position_samples"),
            "profiling_enabled": od.get("sparrow_profiling_enabled", False),
            "profile_search_total_ms": od.get("sparrow_profile_search_total_ms"),
            "profile_session_build_ms": od.get("sparrow_profile_session_build_ms"),
            "profile_deregister_ms": od.get("sparrow_profile_deregister_ms"),
            "profile_candidate_transform_ms": od.get("sparrow_profile_candidate_transform_ms"),
            "profile_cde_query_collect_ms": od.get("sparrow_profile_cde_query_collect_ms"),
            "profile_hazard_loss_ms": od.get("sparrow_profile_hazard_loss_ms"),
            "profile_boundary_check_ms": od.get("sparrow_profile_boundary_check_ms"),
            "profile_broadphase_reject_count": od.get("sparrow_profile_broadphase_reject_count"),
            "profile_early_termination_count": od.get("sparrow_profile_early_termination_count"),
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout", "runtime_ms": (time.time() - t0) * 1000}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "runtime_ms": (time.time() - t0) * 1000}
    finally:
        for p in [in_path, out_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


# ── cost breakdown builder ────────────────────────────────────────────────────

_NOT_AVAILABLE = "not_available"

def _build_profile_json(run: dict) -> dict[str, Any]:
    """Build the canonical profile JSON for a run result."""
    profiled = run.get("profiling_enabled", False)

    def _ms(key: str) -> float | str:
        if not profiled:
            return _NOT_AVAILABLE
        v = run.get(key)
        return round(v, 3) if isinstance(v, float) else (_NOT_AVAILABLE if v is None else v)

    def _cnt(key: str) -> int | str:
        if not profiled:
            return _NOT_AVAILABLE
        v = run.get(key)
        return v if isinstance(v, int) else (_NOT_AVAILABLE if v is None else v)

    sc = run.get("search_calls") or 0
    ss = run.get("search_samples") or 0

    profile = {
        "native_search_calls": sc,
        "candidates_evaluated": ss,
        "session_build_ms": _ms("profile_session_build_ms"),
        "deregister_reregister_ms": (
            _ms("profile_deregister_ms") if profiled else _NOT_AVAILABLE
        ),
        "candidate_transform_prepare_ms": _ms("profile_candidate_transform_ms"),
        "cde_query_collect_ms": _ms("profile_cde_query_collect_ms"),
        "specialized_pipeline_ms": _ms("profile_cde_query_collect_ms"),  # same code path
        "hazard_loss_ms": {
            "value": _NOT_AVAILABLE,
            "note": "hazard quantification is inside cde_query_collect; not separately timed to avoid double overhead",
        },
        "boundary_check_ms": _ms("profile_boundary_check_ms"),
        "broadphase_reject_count": _cnt("profile_broadphase_reject_count"),
        "early_termination_count": _cnt("profile_early_termination_count"),
    }

    # Top-costs breakdown (% of total search ms)
    top_costs: list[dict] = []
    if profiled:
        search_total = run.get("profile_search_total_ms") or 0.0
        buckets = {
            "cde_query_collect_ms": run.get("profile_cde_query_collect_ms") or 0.0,
            "candidate_transform_prepare_ms": run.get("profile_candidate_transform_ms") or 0.0,
            "session_build_ms": run.get("profile_session_build_ms") or 0.0,
            "deregister_ms": run.get("profile_deregister_ms") or 0.0,
            "boundary_check_ms": run.get("profile_boundary_check_ms") or 0.0,
        }
        accounted = sum(buckets.values())
        other_ms = max(0.0, search_total - accounted)
        buckets["other_unaccounted_ms"] = other_ms
        denom = search_total if search_total > 0 else 1.0
        top_costs = sorted(
            [{"name": k, "ms": round(v, 2), "percent": round(v / denom * 100, 1)}
             for k, v in buckets.items()],
            key=lambda x: x["ms"], reverse=True
        )

    return {
        "profiling_enabled": profiled,
        "search_total_ms": _ms("profile_search_total_ms"),
        "profile": profile,
        "top_costs_percent": top_costs,
    }


# ── cases ─────────────────────────────────────────────────────────────────────

def _run_medium_case(seed: int, time_secs: int) -> dict[str, Any]:
    print(f"\n--- medium (jakobs2, 25 instances): profiling with SGH_Q29_CDE_PROFILE=1 ---")
    spp_path = UPSTREAM_INPUT_DIR / "jakobs2.json"
    if not spp_path.exists():
        return {"case_id": "medium", "status": "error", "error": "jakobs2.json not found",
                "runtime_ms": 0, "profile": {}, "top_costs_percent": []}
    solver_input = _spp_to_local_input(spp_path, time_secs, seed, "medium")
    run = _run_local_profiled(solver_input)
    print(f"  status={run.get('status')} runtime={run.get('runtime_ms','?'):.0f}ms "
          f"pairs={run.get('final_pairs','?')} search_calls={run.get('search_calls','?')} "
          f"profiling={run.get('profiling_enabled','?')}")
    pj = _build_profile_json(run)
    return {
        "case_id": "medium",
        "status": run.get("status", "ok"),
        "runtime_ms": run.get("runtime_ms", 0),
        "placed_count": run.get("placed_count"),
        "final_pairs": run.get("final_pairs"),
        "iterations": run.get("iterations"),
        "search_calls": run.get("search_calls"),
        **pj,
    }


def _run_lv8_subset_case(seed: int, time_secs: int) -> dict[str, Any]:
    print(f"\n--- lv8_subset (3 LV8 part types, ~67 instances): profiling ---")
    if not DENSE191_FIXTURE.exists():
        return {"case_id": "lv8_subset", "status": "error", "error": "fixture not found",
                "runtime_ms": 0, "profile": {}, "top_costs_percent": []}
    fixture = json.loads(DENSE191_FIXTURE.read_text())
    parts = fixture["parts"][:3]
    stocks = fixture["stocks"]
    solver_input = _lv8_input(parts, stocks, time_secs, seed, "lv8_subset")
    run = _run_local_profiled(solver_input)
    total_inst = sum(p.get("quantity", 1) for p in parts)
    print(f"  status={run.get('status')} runtime={run.get('runtime_ms','?'):.0f}ms "
          f"pairs={run.get('final_pairs','?')} search_calls={run.get('search_calls','?')} "
          f"instances={total_inst} profiling={run.get('profiling_enabled','?')}")
    pj = _build_profile_json(run)
    return {
        "case_id": "lv8_subset",
        "status": run.get("status", "ok"),
        "runtime_ms": run.get("runtime_ms", 0),
        "placed_count": run.get("placed_count"),
        "final_pairs": run.get("final_pairs"),
        "iterations": run.get("iterations"),
        "search_calls": run.get("search_calls"),
        **pj,
    }


def _run_dense191_case(seed: int, time_secs: int) -> dict[str, Any]:
    print(f"\n--- dense191 (all 191 LV8 instances): profiling (capped at {time_secs}s) ---")
    if not DENSE191_FIXTURE.exists():
        return {"case_id": "dense191", "status": "error", "error": "fixture not found",
                "runtime_ms": 0, "profile": {}, "top_costs_percent": []}
    fixture = json.loads(DENSE191_FIXTURE.read_text())
    parts = fixture["parts"]
    stocks = fixture["stocks"]
    solver_input = _lv8_input(parts, stocks, time_secs, seed, "dense191")
    run = _run_local_profiled(solver_input)
    print(f"  status={run.get('status')} runtime={run.get('runtime_ms','?'):.0f}ms "
          f"pairs={run.get('final_pairs','?')} search_calls={run.get('search_calls','?')} "
          f"profiling={run.get('profiling_enabled','?')}")
    pj = _build_profile_json(run)
    return {
        "case_id": "dense191",
        "status": run.get("status", "ok"),
        "runtime_ms": run.get("runtime_ms", 0),
        "placed_count": run.get("placed_count"),
        "final_pairs": run.get("final_pairs"),
        "iterations": run.get("iterations"),
        "search_calls": run.get("search_calls"),
        **pj,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    print("=== SGH-Q29 Phase B: local CDE hotspot profiler ===")

    if not LOCAL_BIN.exists():
        print(f"ERROR: local binary not found: {LOCAL_BIN}")
        return 2

    seed = 42
    cases = []
    cases.append(_run_medium_case(seed=seed, time_secs=20))
    cases.append(_run_lv8_subset_case(seed=seed, time_secs=30))
    cases.append(_run_dense191_case(seed=seed, time_secs=60))

    any_profiled = any(c.get("profiling_enabled") for c in cases)
    # "partial" is acceptable — solver ran but did not converge within time limit
    all_ran = all(c.get("status") in ("ok", "partial") for c in cases)
    status = "PASS" if (all_ran and any_profiled) else "FAIL"

    summary = {
        "task": "sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler",
        "phase": "local_cde_hotspot_profiler",
        "status": status,
        "profile_flag": "SGH_Q29_CDE_PROFILE=1",
        "local_binary": str(LOCAL_BIN.relative_to(ROOT)),
        "notes": {
            "hazard_loss_ms": "not separately timed; hazard quantification is inside CDE query path (cde_query_collect_ms). Timing both would add overhead without additional insight.",
            "deregister_reregister_ms": "deregister measured in search.rs (allowed file); reregister is in worker.rs (not in Q29 allowed file list). Combined metric partially available.",
            "session_build_ms": "only fallback/cross-sheet session builds measured (most expensive path); primary live-session is built once per worker pass in worker.rs.",
            "specialized_pipeline_ms": "same code path as cde_query_collect_ms (collect_poly_collisions_in_detector_custom); reported as alias.",
        },
        "cases": cases,
    }

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary written to: {SUMMARY_FILE}")

    _write_md_report(summary)
    print(f"Report written to: {REPORT_FILE}")
    print(f"\nPhase B: {status}")
    return 0 if status == "PASS" else 2


def _pct_bar(pct: float, width: int = 20) -> str:
    filled = int(round(pct / 100 * width))
    return "█" * filled + "░" * (width - filled)


def _write_md_report(summary: dict) -> None:
    lines = [
        "# SGH-Q29 Phase B: Local CDE Hotspot Profiler Report",
        "",
        f"**Status: {summary['status']}**",
        "",
        f"Profile flag: `{summary['profile_flag']}`",
        "",
        "## Notes on measurement coverage",
        "",
    ]
    for k, v in summary.get("notes", {}).items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    for c in summary.get("cases", []):
        case_id = c.get("case_id", "?")
        lines += [
            f"## Case: {case_id}",
            "",
            f"- Status: {c.get('status')}",
            f"- Runtime: {c.get('runtime_ms', 0):.0f} ms",
            f"- Placed: {c.get('placed_count', '?')}",
            f"- Final pairs: {c.get('final_pairs', '?')}",
            f"- Iterations: {c.get('iterations', '?')}",
            f"- Search calls: {c.get('search_calls', '?')}",
            f"- Profiling enabled: {c.get('profiling_enabled', False)}",
            f"- Search total ms: {c.get('search_total_ms', '?')}",
            "",
        ]
        top = c.get("top_costs_percent") or []
        if top:
            lines += ["### Cost breakdown (% of search_total_ms)", ""]
            lines.append("| Component | ms | % | Bar |")
            lines.append("|-----------|-----|---|-----|")
            for row in top:
                pct = row.get("percent", 0)
                bar = _pct_bar(pct)
                lines.append(f"| {row['name']} | {row['ms']:.1f} | {pct:.1f}% | {bar} |")
            lines.append("")
        profile = c.get("profile") or {}
        if profile:
            lines += ["### Profile fields", ""]
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            for k, v in profile.items():
                if isinstance(v, dict):
                    lines.append(f"| {k} | {v.get('value','?')} — {v.get('note','')} |")
                else:
                    lines.append(f"| {k} | {v} |")
            lines.append("")

    REPORT_FILE.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
