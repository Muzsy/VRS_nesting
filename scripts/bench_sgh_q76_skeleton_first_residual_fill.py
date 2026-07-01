#!/usr/bin/env python3
"""SGH-Q76 - Skeleton-first seed + residual-fill (contour residual-space objective) A/B benchmark.

Data-driven verdict for the F1 strategy: partition the structure-determining `Critical` parts, edge-
anchor + PIN them maximizing the contiguous REAL-CONTOUR residual space, then residual-fill the rest
(`direct_insert_on_sheet`, largest-room-first) and let the downstream exploration pack the remainder
around the pinned skeleton. Compared default (gates OFF) vs `VRS_SKELETON_FIRST=1` on TWO packages:

  * Full276  - 2x1500x3000, margin 5 / spacing 5, continuous rotation (the reference LV8 workload).
  * MixedMed - small/medium parts, NO dominant big anchor (genericity probe).

Result-centric (no proxy): placed_count + utilization + Q76 contour residual diagnostics + validity
(final_pairs == 0). ACCEPT only if skeleton-first generically does NOT regress the default on BOTH
packages (placed AND util), valid; otherwise an HONEST EXIT verdict is recorded (-> F3 / rethink).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from render_sgh_q47_q50_benchmark_artifacts import render_run

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
Q49_INPUT = ROOT / "artifacts/benchmarks/sgh_q49/inputs/q49_full276_6x1500x3000_margin5_spacing8_continuous_300.json"
TASK_NO = 76
Q76 = ROOT / "artifacts" / "benchmarks" / f"sgh_q{TASK_NO}"
INPUTS = Q76 / "inputs"
OUTPUTS = Q76 / "outputs"
LOGS = Q76 / "logs"

# The skeleton-first gate (default OFF in production). The A/B "default" arm clears it.
SKELETON_GATES = {"VRS_SKELETON_FIRST": "1"}
# Every gate that could perturb the seed path is cleared on BOTH arms for a clean comparison.
CLEAR_KEYS = list(SKELETON_GATES) + [
    "VRS_SKELETON_FRAC",
    "VRS_SHEET_BUILDER",
    "VRS_SHEET_BUILDER_SKELETON",
    "VRS_SHEET_BUILDER_FORCE_LATEST",
    "VRS_SHEET_BUILDER_STRICT_LATEST",
    "VRS_EDGE_INTERLOCK_SEED",
    "VRS_BIG_ROW_SEED",
    "VRS_ANCHOR_CATALOG",
    "VRS_FEATURE_CANDIDATES",
    "VRS_BPP_COMPRESS",
    "VRS_BPP_DENSITY_COMPACT",
    "VRS_BPP_LNS",
    "VRS_MULTISHEET_MODE",
]


def poly_area(pts: list[list[float]]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def full276_parts() -> list[dict[str, Any]]:
    parts = copy.deepcopy(json.loads(Q49_INPUT.read_text())["parts"])
    for part in parts:
        part.pop("allowed_rotations_deg", None)
        part.pop("rotation_policy", None)
    return parts


def mixed_medium_parts() -> list[dict[str, Any]]:
    """A generic small/medium package with NO dominant big anchor (genericity probe)."""
    def rect(pid: str, qty: int, w: float, h: float) -> dict[str, Any]:
        return {"id": pid, "quantity": qty, "width": w, "height": h,
                "outer_points": [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]}

    def lshape(pid: str, qty: int, s: float) -> dict[str, Any]:
        return {"id": pid, "quantity": qty, "width": s, "height": s,
                "outer_points": [[0.0, 0.0], [s, 0.0], [s, s * 0.4],
                                 [s * 0.4, s * 0.4], [s * 0.4, s], [0.0, s]]}

    return [
        rect("m_300x200", 30, 300.0, 200.0),
        rect("m_250x250", 20, 250.0, 250.0),
        rect("m_400x150", 16, 400.0, 150.0),
        rect("m_180x180", 30, 180.0, 180.0),
        rect("m_220x320", 14, 220.0, 320.0),
        lshape("l_med", 10, 360.0),
    ]


PACKAGES: dict[str, dict[str, Any]] = {
    "full276": {"parts_fn": full276_parts, "stocks": [{"id": "S1500x3000", "quantity": 2, "width": 1500.0, "height": 3000.0}]},
    "mixedmed": {"parts_fn": mixed_medium_parts, "stocks": [{"id": "S1500x3000", "quantity": 2, "width": 1500.0, "height": 3000.0}]},
}


def build_input(pkg: str, time_limit_s: int) -> Path:
    spec = PACKAGES[pkg]
    inp = {
        "contract_version": "v1",
        "project_name": f"sgh_q76_{pkg}",
        "seed": 42,
        "time_limit_s": time_limit_s,
        "stocks": spec["stocks"],
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "rotation_policy": "continuous",
        "margin_mm": 5.0,
        "spacing_mm": 5.0,
        "kerf_mm": 0.0,
        "parts": spec["parts_fn"](),
    }
    INPUTS.mkdir(parents=True, exist_ok=True)
    path = INPUTS / f"q76_{pkg}_2x1500x3000_margin5_spacing5_continuous_{time_limit_s}.json"
    path.write_text(json.dumps(inp, indent=2))
    return path


def run(run_id: str, inp: Path, time_limit_s: int, skeleton: bool) -> dict[str, Any]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS / f"{run_id}_output.json"
    env = dict(os.environ)
    for key in CLEAR_KEYS:
        env.pop(key, None)
    if skeleton:
        env.update(SKELETON_GATES)
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out_path)],
        capture_output=True, text=True, timeout=time_limit_s + 3600, env=env,
    )
    wall = time.monotonic() - t0
    (LOGS / f"{run_id}.log").write_text(
        f"exit={proc.returncode}\nwall_s={wall:.3f}\nskeleton={skeleton}\nstderr:\n{proc.stderr[:8000]}\n"
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{run_id} exit {proc.returncode}: {proc.stderr[:1500]}")
    out = json.loads(out_path.read_text())
    out["_wall"] = wall
    return out


def summarize(out: dict[str, Any]) -> dict[str, Any]:
    diag = out.get("optimizer_diagnostics") or {}
    bpp = diag.get("bpp_reduction") or {}
    metrics = out.get("metrics") or {}
    placements = out.get("placements") or []
    return {
        "status": out.get("status"),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": metrics.get("unplaced_count"),
        "used_sheets": len({int(p.get("sheet_index", 0)) for p in placements}),
        "utilization_pct": round(float(diag.get("sparrow_ms_utilization_pct") or 0.0), 2),
        "final_pairs": diag.get("sparrow_ms_final_pairs"),
        "boundary_violations": diag.get("sparrow_ms_boundary_violations", diag.get("sparrow_boundary_violations_final")),
        "seed_source": bpp.get("bpp_q69_seed_source"),
        "q76_skeleton_first_used": bpp.get("bpp_q76_skeleton_first_used"),
        "q76_skeleton_count": bpp.get("bpp_q76_skeleton_count"),
        "q76_skeleton_area_frac": round(float(bpp.get("bpp_q76_skeleton_area_frac") or 0.0), 4),
        "q76_largest_free_after_skeleton": round(float(bpp.get("bpp_q76_largest_free_after_skeleton") or 0.0), 0),
        "q76_fill_placed": bpp.get("bpp_q76_fill_placed"),
        "q76_fill_unplaced": bpp.get("bpp_q76_fill_unplaced"),
        "q76_final_largest_free": round(float(bpp.get("bpp_q76_final_largest_free") or 0.0), 0),
        "wall_time_s": round(float(out.get("_wall", 0.0)), 1),
    }


def verdict_for_pkg(d: dict[str, Any], s: dict[str, Any]) -> tuple[bool, str]:
    """skeleton-first must be valid AND not regress default on placed AND util."""
    if s["final_pairs"] not in (0, None) and s["final_pairs"] != 0:
        return False, f"INVALID skeleton run (final_pairs={s['final_pairs']})"
    if not s.get("q76_skeleton_first_used"):
        return False, "skeleton-first gate did not activate"
    placed_ok = (s["placed_count"] or 0) >= (d["placed_count"] or 0)
    util_ok = (s["utilization_pct"] or 0) >= (d["utilization_pct"] or 0) - 0.05
    if placed_ok and util_ok:
        return True, (f"placed {s['placed_count']}>={d['placed_count']}, "
                      f"util {s['utilization_pct']}>=~{d['utilization_pct']}")
    return False, (f"regression: placed {s['placed_count']} vs {d['placed_count']}, "
                   f"util {s['utilization_pct']} vs {d['utilization_pct']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=int, default=240, help="time limit per run (s)")
    ap.add_argument("--packages", nargs="*", default=list(PACKAGES), choices=list(PACKAGES))
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    results: dict[str, Any] = {}
    accept_all = True
    for pkg in args.packages:
        inp = build_input(pkg, args.time)
        input_rel = f"inputs/{inp.name}"
        def_id = f"q76_{pkg}_A_default"
        sk_id = f"q76_{pkg}_B_skeleton_first"
        print(f"[{pkg}] default ...", flush=True)
        d_out = run(def_id, inp, args.time, skeleton=False)
        print(f"[{pkg}] skeleton-first ...", flush=True)
        s_out = run(sk_id, inp, args.time, skeleton=True)
        d, s = summarize(d_out), summarize(s_out)
        ok, why = verdict_for_pkg(d, s)
        accept_all = accept_all and ok
        renders = {}
        if not args.no_render:
            try:
                renders["default"] = render_run(TASK_NO, def_id, input_rel, f"outputs/{def_id}_output.json")
                renders["skeleton_first"] = render_run(TASK_NO, sk_id, input_rel, f"outputs/{sk_id}_output.json")
            except Exception as exc:  # rendering must never fail the data verdict
                renders["error"] = str(exc)
        results[pkg] = {"input": input_rel, "default": d, "skeleton_first": s,
                        "pkg_accept": ok, "pkg_reason": why, "renders": renders}
        print(f"[{pkg}] default placed={d['placed_count']} util={d['utilization_pct']} | "
              f"skeleton placed={s['placed_count']} util={s['utilization_pct']} -> "
              f"{'ACCEPT' if ok else 'EXIT'} ({why})", flush=True)

    summary = {
        "task": "sgh_q76_skeleton_first_residual_fill",
        "time_limit_s": args.time,
        "verdict": "ACCEPT" if accept_all else "EXIT_HONEST",
        "accept_rule": "skeleton-first valid (final_pairs=0) AND >= default placed AND >= default util on EVERY package",
        "packages": results,
    }
    Q76.mkdir(parents=True, exist_ok=True)
    (Q76 / "q76_summary.json").write_text(json.dumps(summary, indent=2))
    write_report(summary)
    print(f"\nVERDICT: {summary['verdict']}")


def write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# SGH-Q76 Report - Skeleton-first seed + residual-fill (contour residual-space objective)",
        "",
        f"## Verdict: {summary['verdict']}",
        "",
        f"- time limit/run: **{summary['time_limit_s']}s**",
        f"- accept rule: {summary['accept_rule']}",
        "",
        "## A/B per package (default vs skeleton-first)",
        "",
        "| package | arm | status | placed | unplaced | used | util % | final_pairs | wall s |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pkg, r in summary["packages"].items():
        for arm in ("default", "skeleton_first"):
            a = r[arm]
            lines.append(
                f"| {pkg} | {arm} | {a['status']} | {a['placed_count']} | {a['unplaced_count']} | "
                f"{a['used_sheets']} | {a['utilization_pct']} | {a['final_pairs']} | {a['wall_time_s']} |"
            )
    lines += ["", "## Q76 skeleton diagnostics (skeleton-first arm)", "",
              "| package | skel_count | skel_area_frac | free_after_skel | fill_placed | fill_unplaced | final_free |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for pkg, r in summary["packages"].items():
        s = r["skeleton_first"]
        lines.append(
            f"| {pkg} | {s['q76_skeleton_count']} | {s['q76_skeleton_area_frac']} | "
            f"{s['q76_largest_free_after_skeleton']} | {s['q76_fill_placed']} | "
            f"{s['q76_fill_unplaced']} | {s['q76_final_largest_free']} |"
        )
    lines += ["", "## Per-package verdict", ""]
    for pkg, r in summary["packages"].items():
        lines.append(f"- **{pkg}**: {'ACCEPT' if r['pkg_accept'] else 'EXIT'} - {r['pkg_reason']}")
    lines.append("")
    (Q76 / "q76_report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
