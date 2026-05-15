#!/usr/bin/env python3
"""LV8 2-sheet Phase C — final multi-seed runs with high work budget."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import sys
import os
import csv as csvmod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "tmp" / "lv8_2sheet_quality_search_20260511"
INPUT_DIR = RUN_DIR / "inputs"
RUN_DIR.mkdir(exist_ok=True)

ENGINE_BIN = REPO_ROOT / "rust" / "nesting_engine" / "target" / "release" / "nesting_engine"
BASE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nesting_engine" / "ne2_input_lv8jav.json"


def load_fixture():
    with open(BASE_FIXTURE) as f:
        return json.load(f)


def build_input(base: dict, sheet_w: float, sheet_h: float, spacing: float, margin: float, rotations: list[int]) -> dict:
    sheet = dict(base["sheet"])
    sheet["width_mm"] = sheet_w
    sheet["height_mm"] = sheet_h
    sheet["spacing_mm"] = spacing
    sheet["margin_mm"] = margin
    parts = []
    for p in base["parts"]:
        for _ in range(p["quantity"]):
            new_p = dict(p)
            new_p["quantity"] = 1
            new_p["allowed_rotations_deg"] = rotations
            parts.append(new_p)
    return {
        "version": "nesting_engine_v2",
        "seed": 42,
        "time_limit_sec": 600,
        "sheet": sheet,
        "parts": parts,
    }


def run_engine(
    input_data: dict,
    cli_args: list[str],
    env: dict,
    run_id: str,
    timeout: int = 660,
) -> dict[str, Any]:
    t0 = time.time()
    payload = json.dumps(input_data, separators=(",", ":"))

    proc = subprocess.run(
        [str(ENGINE_BIN), "nest"] + cli_args,
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, **env},
    )
    wall = time.time() - t0

    stdout_path = RUN_DIR / f"{run_id}.stdout.json"
    stderr_path = RUN_DIR / f"{run_id}.stderr.log"
    with open(stdout_path, "w") as f:
        f.write(proc.stdout)
    with open(stderr_path, "w") as f:
        f.write(proc.stderr)

    result = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cli_args": cli_args,
        "env_keys": sorted(env.keys()),
        "returncode": proc.returncode,
        "wall_time_sec": round(wall, 3),
        "status": "unknown",
        "placed_count": 0,
        "unplaced_count": 0,
        "sheets_used": 0,
        "utilization_pct": 0.0,
        "valid": None,
        "validation_summary": "",
        "fallback_warnings": [],
        "diag_summary": {},
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "engine_elapsed_sec": None,
        "sa_iters_actual": None,
    }

    out = {}
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception:
        pass

    if out:
        result["engine_elapsed_sec"] = out.get("elapsed_sec")
        result["status"] = out.get("status", "unknown")
        result["placed_count"] = len(out.get("placements", []))
        result["unplaced_count"] = len(out.get("unplaced", []))
        result["sheets_used"] = out.get("sheets_used", 0)
        obj = out.get("objective", {})
        result["utilization_pct"] = round(obj.get("utilization_pct", 0.0), 3)

        # Parse SA iters
        for line in proc.stderr.split("\n"):
            for prefix in ["SA iters:", "SA iterations:", "effective_iters="]:
                if prefix in line:
                    try:
                        parts = line.split(prefix)
                        val = parts[1].strip().split()[0].rstrip(",)")
                        result["sa_iters_actual"] = int(val)
                        break
                    except Exception:
                        pass

    # Parse diagnostic counters from stderr
    diag = {}
    for line in proc.stderr.split("\n"):
        if "budget_remaining=Some(0)" in line:
            diag["budget_exhausted"] = True
        if "stop_mode=" in line and "wall_clock" in line:
            diag["stop_mode"] = "wall_clock"
    for key in ["sa_eval_count", "can_place_calls", "cfr_calls"]:
        for line in proc.stderr.split("\n"):
            if f"{key}:" in line:
                try:
                    parts = line.split(f"{key}:")
                    diag[key] = int(parts[1].strip().split()[0])
                except Exception:
                    pass
    result["diag_summary"] = diag

    # Fallback warnings
    for line in proc.stderr.split("\n"):
        if any(kw in line.lower() for kw in ["fallback", "warning", "error"]):
            if "NEST_" not in line and "BLF_" not in line and "SEARCH" not in line and "GREEDY" not in line:
                result["fallback_warnings"].append(line.strip())

    return result


def validate_run(result: dict) -> dict[str, Any]:
    """Basic validation of placement output."""
    stdout_path = Path(result["stdout_path"])
    if not stdout_path.exists():
        return {"valid": None, "summary": "no stdout"}

    try:
        with open(stdout_path) as f:
            out = json.load(f)
    except Exception as e:
        return {"valid": False, "summary": f"parse error: {e}"}

    placements = out.get("placements", [])
    unplaced = out.get("unplaced", [])
    status = out.get("status")

    summary = f"status={status}, placed={len(placements)}, unplaced={len(unplaced)}, sheets={out.get('sheets_used', 0)}"

    if status == "ok" and len(placements) >= 276 and len(unplaced) == 0:
        return {"valid": True, "summary": summary}
    elif status == "partial" and len(placements) > 0:
        return {"valid": True, "summary": summary + " (partial ok)"}
    else:
        return {"valid": False, "summary": summary}


def main():
    base = load_fixture()
    print("=== LV8 2-sheet Phase C — multi-seed final runs ===")

    # Best config from Phase B: BLF + SA + slide on 3000x1500 r90
    # With high work budget to prevent premature budget exhaustion
    ROT90 = [0, 90, 180, 270]
    best_input = build_input(base, 3000, 1500, 10, 10, ROT90)

    # Ensure input is saved
    input_path = INPUT_DIR / "s3000x1500_r90_final.json"
    with open(input_path, "w") as f:
        json.dump(best_input, f)

    print(f"Input: {len(best_input['parts'])} parts, sheet=3000x1500, rot=[0,90,180,270], gap=10, margin=10")

    # Env with high work budget (5x default to allow 5 greedy evals in 600s)
    env_high = {
        "NESTING_ENGINE_SA_DIAG": "1",
        "NESTING_ENGINE_EMIT_NFP_STATS": "1",
        "NESTING_ENGINE_WORK_UNITS_PER_SEC": "125000",  # 2.5x default (was 50K)
    }

    results = []

    # Phase C runs: multi-seed with high work budget
    configs = [
        # (sa_iters, eval_budget, seed, time_limit, label)
        (32, 5, 42, 300, "C1_sa32_e5_s42_300s"),
        (32, 5, 1, 300, "C2_sa32_e5_s1_300s"),
        (32, 5, 7, 300, "C3_sa32_e5_s7_300s"),
        (64, 5, 42, 600, "C4_sa64_e5_s42_600s"),
        (64, 5, 1, 600, "C5_sa64_e5_s1_600s"),
        (64, 5, 7, 600, "C6_sa64_e5_s7_600s"),
        (64, 5, 11, 600, "C7_sa64_e5_s11_600s"),
        (64, 5, 101, 600, "C8_sa64_e5_s101_600s"),
        (128, 10, 42, 600, "C9_sa128_e10_s42_600s"),
        (64, 10, 42, 600, "C10_sa64_e10_s42_600s"),
    ]

    for sa_iters, eval_budget, seed, time_limit, label in configs:
        run_id = label
        print(f"\nRunning {run_id} (iters={sa_iters}, eval={eval_budget}s, seed={seed}, limit={time_limit}s)...")

        cli_args = [
            "--placer", "blf",
            "--search", "sa",
            "--compaction", "slide",
            "--sa-iters", str(sa_iters),
            "--sa-eval-budget-sec", str(eval_budget),
            "--sa-seed", str(seed),
        ]

        r = run_engine(best_input, cli_args, env_high, run_id, timeout=time_limit + 60)
        r.update({
            "input_key": "s3000x1500_r90",
            "placer": "blf",
            "search": "sa",
            "compaction": "slide",
            "part_in_part": "off",
            "nfp_kernel": None,
            "sa_iters_requested": sa_iters,
            "sa_eval_budget_sec": eval_budget,
            "seed": seed,
            "time_limit_sec": time_limit,
            "rotation_profile": "r90",
            "label": label,
            "work_units_per_sec": 125000,
        })

        val = validate_run(r)
        r["valid"] = val.get("valid")
        r["validation_summary"] = val.get("summary", "")

        placed = r["placed_count"]
        unplaced = r["unplaced_count"]
        sheets = r["sheets_used"]
        util = r["utilization_pct"]
        wall = r["wall_time_sec"]
        budget_exp = r["diag_summary"].get("budget_exhausted", False)
        print(f"  -> placed={placed}, unplaced={unplaced}, sheets={sheets}, util={util:.2f}%, wall={wall:.1f}s, budget_exhausted={budget_exp}")

        results.append(r)

    # Also run NFP old_concave with high budget
    nfp_configs = [
        (32, 5, 42, 300, "CN1_nfp_sa32_e5_s42_300s"),
        (64, 5, 42, 600, "CN2_nfp_sa64_e5_s42_600s"),
        (64, 5, 1, 600, "CN3_nfp_sa64_e5_s1_600s"),
    ]

    for sa_iters, eval_budget, seed, time_limit, label in nfp_configs:
        run_id = label
        print(f"\nRunning {run_id} (NFP)...")

        cli_args = [
            "--placer", "nfp",
            "--nfp-kernel", "old_concave",
            "--search", "sa",
            "--compaction", "slide",
            "--sa-iters", str(sa_iters),
            "--sa-eval-budget-sec", str(eval_budget),
            "--sa-seed", str(seed),
        ]

        r = run_engine(best_input, cli_args, env_high, run_id, timeout=time_limit + 60)
        r.update({
            "input_key": "s3000x1500_r90",
            "placer": "nfp",
            "search": "sa",
            "compaction": "slide",
            "part_in_part": "off",
            "nfp_kernel": "old_concave",
            "sa_iters_requested": sa_iters,
            "sa_eval_budget_sec": eval_budget,
            "seed": seed,
            "time_limit_sec": time_limit,
            "rotation_profile": "r90",
            "label": label,
            "work_units_per_sec": 125000,
        })

        val = validate_run(r)
        r["valid"] = val.get("valid")
        r["validation_summary"] = val.get("summary", "")

        print(f"  -> placed={r['placed_count']}, unplaced={r['unplaced_count']}, sheets={r['sheets_used']}, util={r['utilization_pct']:.2f}%, wall={r['wall_time_sec']:.1f}s")

        results.append(r)

    # Save runs.jsonl
    runs_path = RUN_DIR / "runs.jsonl"
    with open(runs_path, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Find best
    # Priority: valid + placed=276 + sheets<=2
    candidates = [r for r in results if r["valid"] and r["placed_count"] == 276 and r["sheets_used"] <= 2]
    if candidates:
        best = sorted(candidates, key=lambda x: (x["sheets_used"], -x["utilization_pct"], x["wall_time_sec"]))[0]
        final_status = "PASS"
    else:
        # Best partial by placed count
        sorted_results = sorted(
            [r for r in results if r["placed_count"] > 0],
            key=lambda x: (-x["placed_count"], x.get("sheets_used", 999), -x.get("utilization_pct", 0)),
        )
        best = sorted_results[0] if sorted_results else results[0]
        if best["placed_count"] == 276:
            if best.get("sheets_used", 999) > 2:
                final_status = "PARTIAL"
            else:
                final_status = "PASS"
        else:
            final_status = "PARTIAL"

    print(f"\nBest: {best['label']} — placed={best['placed_count']}, sheets={best['sheets_used']}, util={best['utilization_pct']:.2f}%, wall={best['wall_time_sec']:.1f}s, status={final_status}")

    # Save best candidate
    shutil.copy(best["stdout_path"], RUN_DIR / "best_candidate.stdout.json")
    shutil.copy(best["stderr_path"], RUN_DIR / "best_candidate.stderr.log")
    with open(RUN_DIR / "best_candidate.json", "w") as f:
        with open(best["stdout_path"]) as src:
            f.write(src.read())

    # CSV summary
    csv_path = RUN_DIR / "runs.csv"
    with open(csv_path, "w", newline="") as f:
        w = csvmod.writer(f)
        w.writerow(["run_id", "placer", "nfp_kernel", "sa_iters_req", "sa_iters_act", "eval_budget", "seed",
                    "time_limit", "wall_time", "placed", "unplaced", "sheets", "util_pct", "valid", "status", "diag"])
        for r in results:
            w.writerow([
                r["label"], r["placer"], r.get("nfp_kernel") or "",
                r["sa_iters_requested"], r.get("sa_iters_actual") or "",
                r["sa_eval_budget_sec"], r["seed"], r["time_limit_sec"],
                r["wall_time_sec"], r["placed_count"], r["unplaced_count"],
                r["sheets_used"], r["utilization_pct"], r["valid"],
                r["status"], str(r.get("diag_summary", {})),
            ])
    print(f"CSV: {csv_path}")

    return final_status, best, results


if __name__ == "__main__":
    status, best, results = main()
    print(f"\nPhase C done. Best: {best['label']} status={status}")
    print(f"placed={best['placed_count']}, sheets={best['sheets_used']}, util={best['utilization_pct']:.2f}%")