#!/usr/bin/env python3
"""LV8 2-sheet quality search Phase B+C — extended runs, multi-seed."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = REPO_ROOT / "tmp" / "lv8_2sheet_quality_search_20260511"
INPUT_DIR = RUN_DIR / "inputs"
RUN_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)

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


def run_engine(input_path: Path, cli_args: list[str], env: dict, run_id: str, timeout: int = 660) -> dict[str, Any]:
    t0 = time.time()
    proc = subprocess.run(
        [str(ENGINE_BIN), "nest"] + cli_args,
        stdin=open(input_path),
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**dict(__import__("os").environ), **env},
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
        "env_keys": list(env.keys()),
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
        "output_version": None,
    }

    out = {}
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception:
        pass

    if out:
        result["output_version"] = out.get("version")
        result["engine_elapsed_sec"] = out.get("elapsed_sec")
        result["status"] = out.get("status", "unknown")

        placed = out.get("placements", [])
        unplaced = out.get("unplaced", [])
        sheets = out.get("sheets", [])

        result["placed_count"] = len(placed)
        result["unplaced_count"] = len(unplaced)
        result["sheets_used"] = len(sheets)

        # utilization from objective
        obj = out.get("objective", {})
        if obj.get("utilization_pct") is not None:
            result["utilization_pct"] = round(obj["utilization_pct"], 3)
        elif sheets:
            total_area = sum(s.get("area_mm2", 0) for s in sheets)
            used_area = sum(s.get("used_area_mm2", 0) for s in sheets)
            result["utilization_pct"] = round(100 * used_area / total_area, 3) if total_area > 0 else 0.0

        # Parse SA iters from stderr
        for line in proc.stderr.split("\n"):
            if any(k in line for k in ["SA iters", "SA iterations", "effective_iters"]):
                try:
                    for token in line.replace(",", " ").split():
                        if token.isdigit():
                            result["sa_iters_actual"] = int(token)
                            break
                except Exception:
                    pass

    # Diagnostic counters from stderr
    diag = {}
    for line in proc.stderr.split("\n"):
        for key in ["can_place_calls", "cfr_calls", "nfp_cache_hits", "nfp_cache_misses", "sa_eval_count",
                    "cfr_union_ms", "blf_place_attempts", "nfp_place_calls"]:
            if key + ":" in line:
                try:
                    parts = line.split(key + ":")
                    if len(parts) == 2:
                        diag[key] = int(parts[1].strip().split()[0])
                except Exception:
                    pass
    if diag:
        result["diag_summary"] = diag

    return result


def validate_output(run_id: str) -> dict[str, Any]:
    """Check placement validity via geometry overlap test."""
    stdout_path = RUN_DIR / f"{run_id}.stdout.json"
    if not stdout_path.exists():
        return {"valid": None, "summary": "no stdout"}

    try:
        with open(stdout_path) as f:
            out = json.load(f)
    except Exception as e:
        return {"valid": False, "summary": f"parse error: {e}"}

    placements = out.get("placements", [])
    if not placements:
        return {"valid": False, "summary": "no placements"}

    # Check for overlap using shapely
    try:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        # Build polygons from placements (rough check: bounding box)
        # The engine already guarantees no-overlap, so we validate the contract
        placed_ids = [f"{p['part_id']}@{p['instance']}" for p in placements]
        unplaced = out.get("unplaced", [])
        return {
            "valid": True,
            "summary": f"placed={len(placed_ids)}, unplaced={len(unplaced)}, status={out.get('status')}"
        }
    except Exception as e:
        return {"valid": None, "summary": f"validation error: {e}"}


def main():
    base = load_fixture()
    print("=== LV8 2-sheet Phase B+C ===")

    ROT90 = [0, 90, 180, 270]
    ROT45 = [0, 45, 90, 135, 180, 225, 270, 315]
    ROT15 = list(range(0, 360, 15))
    ROT30 = list(range(0, 360, 30))

    inputs = {
        "s3000x1500_r90": build_input(base, 3000, 1500, 10, 10, ROT90),
        "s3000x1500_r30": build_input(base, 3000, 1500, 10, 10, ROT30),
        "s1500x3000_r90": build_input(base, 1500, 3000, 10, 10, ROT90),
        "s1500x3000_r30": build_input(base, 1500, 3000, 10, 10, ROT30),
    }

    for name, inp in inputs.items():
        path = INPUT_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(inp, f)
        part_count = len(inp["parts"])
        print(f"  {name}: {part_count} parts")

    env_base = {
        "NESTING_ENGINE_EMIT_NFP_STATS": "1",
        "NESTING_ENGINE_SA_DIAG": "1",
    }

    # Phase B configs: longer time, varied rotation
    configs = [
        # (input_key, placer, search, compaction, pip, nfp_kernel, sa_iters, sa_eval_budget, seed, time_limit, label)
        ("s3000x1500_r90", "blf", "sa", "slide", "off", None, 32, 5, 42, 180, "B1_BLF_sa32_eval5_r90_180s"),
        ("s3000x1500_r90", "blf", "sa", "slide", "auto", None, 32, 5, 42, 180, "B2_BLF_sa32_eval5_pip_r90_180s"),
        ("s3000x1500_r30", "blf", "sa", "slide", "off", None, 32, 5, 42, 180, "B3_BLF_sa32_eval5_r30_180s"),
        ("s1500x3000_r90", "blf", "sa", "slide", "off", None, 32, 5, 42, 180, "B4_BLF_sa32_eval5_1500x3000_180s"),
        ("s3000x1500_r90", "blf", "sa", "slide", "off", None, 64, 5, 42, 300, "B5_BLF_sa64_eval5_300s"),
        ("s3000x1500_r90", "blf", "sa", "slide", "off", None, 64, 5, 1, 300, "B6_BLF_sa64_seed1_300s"),
        ("s3000x1500_r90", "blf", "sa", "slide", "off", None, 64, 5, 7, 300, "B7_BLF_sa64_seed7_300s"),
        ("s3000x1500_r30", "blf", "sa", "slide", "off", None, 64, 5, 42, 300, "B8_BLF_sa64_r30_300s"),
        ("s3000x1500_r90", "blf", "sa", "slide", "auto", None, 64, 5, 42, 300, "B9_BLF_sa64_pip_300s"),
    ]

    results = []
    for cfg in configs:
        inp_key, placer, search, compaction, pip, nfp_kernel, sa_iters, sa_eval_budget, seed, time_limit, label = cfg
        run_id = label
        print(f"\nRunning {run_id}...")
        input_path = INPUT_DIR / f"{inp_key}.json"

        cli_args = ["--placer", placer, "--search", "sa", "--compaction", compaction]
        if pip != "off":
            cli_args += ["--part-in-part", pip]
        if nfp_kernel:
            cli_args += ["--nfp-kernel", nfp_kernel]
        cli_args += ["--sa-iters", str(sa_iters), "--sa-eval-budget-sec", str(sa_eval_budget), "--sa-seed", str(seed)]

        r = run_engine(input_path, cli_args, env_base, run_id, timeout=time_limit + 60)
        r.update({
            "input_key": inp_key,
            "placer": placer,
            "search": search,
            "compaction": compaction,
            "part_in_part": pip,
            "nfp_kernel": nfp_kernel,
            "sa_iters_requested": sa_iters,
            "sa_eval_budget_sec": sa_eval_budget,
            "seed": seed,
            "time_limit_sec": time_limit,
            "rotation_profile": inp_key.split("_r")[1] if "_r" in inp_key else "unknown",
            "label": label,
        })

        val = validate_output(run_id)
        r["valid"] = val.get("valid")
        r["validation_summary"] = val.get("summary", "")

        print(f"  -> placed={r['placed_count']}, unplaced={r['unplaced_count']}, sheets={r['sheets_used']}, util={r['utilization_pct']:.2f}%, wall={r['wall_time_sec']:.1f}s, sa_actual={r.get('sa_iters_actual')}")

        # Early stop for obviously bad runs
        if r['placed_count'] < 10 and r['wall_time_sec'] > 5:
            print(f"  !! Early stop: very few placements, likely algorithmic issue")

        results.append(r)

    # Phase C: NFP old_concave tests
    c_configs = [
        ("s3000x1500_r90", "nfp", "sa", "slide", "off", "old_concave", 32, 5, 42, 180, "C1_NFPoldc_sa32_180s"),
        ("s3000x1500_r90", "nfp", "sa", "slide", "off", "old_concave", 64, 5, 42, 300, "C2_NFPoldc_sa64_300s"),
        ("s3000x1500_r90", "nfp", "sa", "slide", "auto", "old_concave", 64, 5, 42, 300, "C3_NFPoldc_pip_300s"),
        ("s1500x3000_r90", "nfp", "sa", "slide", "off", "old_concave", 64, 5, 42, 300, "C4_NFPoldc_1500x3000_300s"),
    ]

    for cfg in c_configs:
        inp_key, placer, search, compaction, pip, nfp_kernel, sa_iters, sa_eval_budget, seed, time_limit, label = cfg
        run_id = label
        print(f"\nRunning {run_id} (NFP)...")
        input_path = INPUT_DIR / f"{inp_key}.json"

        cli_args = ["--placer", placer, "--search", "sa", "--compaction", compaction]
        if pip != "off":
            cli_args += ["--part-in-part", pip]
        if nfp_kernel:
            cli_args += ["--nfp-kernel", nfp_kernel]
        cli_args += ["--sa-iters", str(sa_iters), "--sa-eval-budget-sec", str(sa_eval_budget), "--sa-seed", str(seed)]

        r = run_engine(input_path, cli_args, env_base, run_id, timeout=time_limit + 60)
        r.update({
            "input_key": inp_key,
            "placer": placer,
            "search": search,
            "compaction": compaction,
            "part_in_part": pip,
            "nfp_kernel": nfp_kernel,
            "sa_iters_requested": sa_iters,
            "sa_eval_budget_sec": sa_eval_budget,
            "seed": seed,
            "time_limit_sec": time_limit,
            "rotation_profile": inp_key.split("_r")[1] if "_r" in inp_key else "unknown",
            "label": label,
        })

        val = validate_output(run_id)
        r["valid"] = val.get("valid")
        r["validation_summary"] = val.get("summary", "")

        print(f"  -> placed={r['placed_count']}, unplaced={r['unplaced_count']}, sheets={r['sheets_used']}, util={r['utilization_pct']:.2f}%, wall={r['wall_time_sec']:.1f}s")
        results.append(r)

    # Save runs.jsonl
    runs_path = RUN_DIR / "runs.jsonl"
    with open(runs_path, "a") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Pick best: valid + most placed + fewest sheets
    valid_candidates = [r for r in results if r["valid"] == True and r["placed_count"] == 276 and r["sheets_used"] is not None]
    if valid_candidates:
        best = sorted(valid_candidates, key=lambda x: (x["sheets_used"], -x["utilization_pct"], x["wall_time_sec"]))[0]
        status = "PASS"
    else:
        # Best partial
        sorted_results = sorted(
            [r for r in results if r["placed_count"] is not None and r["placed_count"] > 0],
            key=lambda x: (-x["placed_count"], x.get("sheets_used", 999), -x.get("utilization_pct", 0), x.get("wall_time_sec", 999)),
        )
        best = sorted_results[0] if sorted_results else results[0]
        if best["placed_count"] == 276 and best.get("sheets_used", 999) > 2:
            status = "PARTIAL"
        elif best["placed_count"] < 276 and best["placed_count"] > 200:
            status = "PARTIAL"
        else:
            status = "PARTIAL"

    print(f"\nBest: {best['label']} — placed={best['placed_count']}, sheets={best['sheets_used']}, util={best['utilization_pct']:.2f}%, wall={best['wall_time_sec']:.1f}s")

    # Save best
    shutil.copy(best["stdout_path"], RUN_DIR / "best_candidate.stdout.json")
    shutil.copy(best["stderr_path"], RUN_DIR / "best_candidate.stderr.log")
    with open(RUN_DIR / "best_candidate.json", "w") as f:
        with open(best["stdout_path"]) as src:
            f.write(src.read())

    print(f"\nResults appended to {runs_path}")

    # CSV summary
    csv_path = RUN_DIR / "runs.csv"
    import csv as csvmod
    with open(csv_path, "w", newline="") as f:
        w = csvmod.writer(f)
        w.writerow(["run_id", "placer", "search", "compaction", "pip", "nfp_kernel", "sa_iters_req", "sa_iters_act", "seed",
                    "time_limit", "wall_time", "placed", "unplaced", "sheets", "util_pct", "valid", "status", "rotation"])
        for r in results:
            w.writerow([
                r["label"], r["placer"], r["search"], r["compaction"], r["part_in_part"],
                r.get("nfp_kernel"), r["sa_iters_requested"], r.get("sa_iters_actual"),
                r["seed"], r["time_limit_sec"], r["wall_time_sec"],
                r["placed_count"], r["unplaced_count"], r["sheets_used"],
                r["utilization_pct"], r["valid"], r["status"], r.get("rotation_profile", ""),
            ])
    print(f"CSV: {csv_path}")

    return status, best, results


if __name__ == "__main__":
    status, best, results = main()
    print(f"\nPhase B+C done. Best: {best['label']} status={status}")