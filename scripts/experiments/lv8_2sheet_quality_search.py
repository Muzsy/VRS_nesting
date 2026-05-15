#!/usr/bin/env python3
"""LV8 2-sheet quality search harness — Phase A sweep."""

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
        d = json.load(f)
    return d


def build_input(
    base: dict,
    sheet_w: float,
    sheet_h: float,
    spacing: float,
    margin: float,
    rotations: list[int],
    extra_parts: list[dict] | None = None,
) -> dict:
    """Create a modified engine input."""
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
    if extra_parts:
        parts.extend(extra_parts)
    return {
        "version": "nesting_engine_v2",
        "seed": 42,
        "time_limit_sec": 600,
        "sheet": sheet,
        "parts": parts,
    }


def run_engine(input_path: Path, cli_args: list[str], env: dict, run_id: str, timeout: int = 660) -> dict[str, Any]:
    """Run the engine and collect metrics."""
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

    result = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cli_args": cli_args,
        "env_keys": list(env.keys()),
        "returncode": proc.returncode,
        "wall_time_sec": round(wall, 3),
        "status": "unknown",
        "placed_count": None,
        "unplaced_count": None,
        "sheets_used": None,
        "utilization_pct": None,
        "valid": None,
        "validation_summary": "",
        "fallback_warnings": [],
        "diag_summary": {},
        "stdout_path": str(RUN_DIR / f"{run_id}.stdout.json"),
        "stderr_path": str(RUN_DIR / f"{run_id}.stderr.log"),
        "engine_elapsed_sec": None,
        "sa_iters_actual": None,
    }

    with open(RUN_DIR / f"{run_id}.stdout.json", "w") as f:
        f.write(proc.stdout)
    with open(RUN_DIR / f"{run_id}.stderr.log", "w") as f:
        f.write(proc.stderr)

    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception:
        out = {}

    if out:
        result["engine_elapsed_sec"] = out.get("elapsed_sec")
        placed = out.get("placed", [])
        result["placed_count"] = len(placed)
        unplaced = out.get("unplaced", [])
        result["unplaced_count"] = len(unplaced)
        sheets = out.get("sheets", [])
        result["sheets_used"] = len(sheets)
        total_area = sum(s.get("area_mm2", 0) for s in sheets)
        used_area = sum(s.get("used_area_mm2", 0) for s in sheets)
        result["utilization_pct"] = round(100 * used_area / total_area, 3) if total_area > 0 else None
        result["status"] = out.get("status", "unknown")

        # Parse SA iterations from stderr
        for line in proc.stderr.split("\n"):
            if "SA iters:" in line or "SA iterations" in line:
                try:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if "iter" in p.lower() and i + 1 < len(parts):
                            result["sa_iters_actual"] = int(parts[i + 1].strip("(),"))
                            break
                except Exception:
                    pass

    # Fallback warnings from stderr
    for line in proc.stderr.split("\n"):
        if any(kw in line.lower() for kw in ["fallback", "warning", "error", "invalid"]):
            result["fallback_warnings"].append(line.strip())

    # Parse diagnostic counters from stderr
    diag = {}
    for line in proc.stderr.split("\n"):
        for prefix in ["can_place_calls:", "cfr_calls:", "nfp_cache_hit", "nfp_cache_miss", "sa_eval_count:"]:
            if prefix in line:
                try:
                    parts = line.split(prefix)
                    if len(parts) == 2:
                        key = prefix.rstrip(":")
                        diag[key] = int(parts[1].strip().split()[0])
                except Exception:
                    pass
    if diag:
        result["diag_summary"] = diag

    return result


def validate_output(run_id: str) -> dict[str, Any]:
    """Run the validator if available."""
    validator_script = REPO_ROOT / "scripts" / "validate_nesting_solution.py"
    stdout_path = RUN_DIR / f"{run_id}.stdout.json"
    if not validator_script.exists() or not stdout_path.exists():
        return {"valid": None, "summary": "validator not available"}
    try:
        result = subprocess.run(
            ["python3", str(validator_script), str(stdout_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return {"valid": True, "summary": result.stdout[:200]}
        else:
            return {"valid": False, "summary": result.stderr[:200]}
    except Exception as e:
        return {"valid": None, "summary": str(e)[:200]}


def main():
    base = load_fixture()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate inputs
    ROT90 = [0, 90, 180, 270]
    ROT45 = [0, 45, 90, 135, 180, 225, 270, 315]
    ROT15 = list(range(0, 360, 15))

    inputs = {
        "s3000x1500_r90": build_input(base, 3000, 1500, 10, 10, ROT90),
        "s3000x1500_r45": build_input(base, 3000, 1500, 10, 10, ROT45),
        "s3000x1500_r15": build_input(base, 3000, 1500, 10, 10, ROT15),
        "s1500x3000_r90": build_input(base, 1500, 3000, 10, 10, ROT90),
        "s1500x3000_r45": build_input(base, 1500, 3000, 10, 10, ROT45),
        "s1500x3000_r15": build_input(base, 1500, 3000, 10, 10, ROT15),
    }

    for name, inp in inputs.items():
        path = INPUT_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump(inp, f)
        part_count = len(inp["parts"])
        total_area = sum(
            abs(sum(
                inp["parts"][i]["outer_points_mm"][j][0] * inp["parts"][i]["outer_points_mm"][(j + 1) % len(inp["parts"][i]["outer_points_mm"])][1] -
                inp["parts"][i]["outer_points_mm"][(j + 1) % len(inp["parts"][i]["outer_points_mm"])][0] * inp["parts"][i]["outer_points_mm"][j][1]
                for j in range(len(inp["parts"][i]["outer_points_mm"]))
            )) / 2
            for i in range(part_count)
        )
        sheet_area = inp["sheet"]["width_mm"] * inp["sheet"]["height_mm"]
        print(f"  {name}: {part_count} parts, sheet={sheet_area:.0f}mm2, nominal_area={total_area:.1f}mm2, ratio={total_area/sheet_area*100:.1f}%")

    # Phase A configs
    configs = [
        # Format: (input_key, placer, search, compaction, pip, nfp_kernel, sa_iters, sa_eval_budget, seed, time_limit, label)
        ("s3000x1500_r90", "blf", "none", "off", "off", None, 0, 0, 42, 60, "A1_BLFinone_noSearch_noComp"),
        ("s3000x1500_r90", "blf", "none", "slide", "off", None, 0, 0, 42, 60, "A2_BLFinone_slide_noSearch"),
        ("s3000x1500_r90", "blf", "sa", "off", "off", None, 32, 3, 42, 60, "A3_BLFsasearch_noComp"),
        ("s3000x1500_r90", "blf", "sa", "slide", "off", None, 32, 3, 42, 90, "A4_BLFsasearch_slide"),
        ("s3000x1500_r90", "blf", "sa", "slide", "auto", None, 32, 3, 42, 90, "A5_BLFsasearch_slide_pip"),
        ("s3000x1500_r90", "nfp", "sa", "slide", "off", "old_concave", 32, 3, 42, 90, "A6_NFPoldconc_sasearch_slide"),
        ("s3000x1500_r45", "blf", "sa", "slide", "off", None, 32, 3, 42, 90, "A7_BLF_rot45_slide"),
        ("s3000x1500_r15", "blf", "sa", "slide", "off", None, 32, 3, 42, 90, "A8_BLF_rot15_slide"),
    ]

    env_base = {
        "NESTING_ENGINE_EMIT_NFP_STATS": "1",
        "NESTING_ENGINE_SA_DIAG": "1",
        "NESTING_ENGINE_BLF_PROFILE": "1",
    }

    results = []
    for (inp_key, placer, search, compaction, pip, nfp_kernel, sa_iters, sa_eval_budget, seed, time_limit, label) in configs:
        run_id = f"{label}"
        print(f"\nRunning {run_id}...")
        input_path = INPUT_DIR / f"{inp_key}.json"

        cli_args = ["--placer", placer]
        if search != "none":
            cli_args += ["--search", "sa"]
        if compaction != "off":
            cli_args += ["--compaction", compaction]
        if pip != "off":
            cli_args += ["--part-in-part", pip]
        if nfp_kernel:
            cli_args += ["--nfp-kernel", nfp_kernel]
        if sa_iters > 0:
            cli_args += ["--sa-iters", str(sa_iters)]
        if sa_eval_budget > 0:
            cli_args += ["--sa-eval-budget-sec", str(sa_eval_budget)]
        if search == "sa":
            cli_args += ["--sa-seed", str(seed)]

        r = run_engine(input_path, cli_args, env_base, run_id, timeout=time_limit + 30)
        r["label"] = label
        r["input_key"] = inp_key
        r["sa_iters_requested"] = sa_iters
        r["sa_eval_budget_sec"] = sa_eval_budget if sa_eval_budget > 0 else None
        r["time_limit_sec"] = time_limit
        r["rotation_profile"] = inp_key.split("_r")[1] if "_r" in inp_key else "unknown"

        val = validate_output(run_id)
        r["valid"] = val.get("valid")
        r["validation_summary"] = val.get("summary", "")

        print(f"  -> placed={r['placed_count']}, unplaced={r['unplaced_count']}, sheets={r['sheets_used']}, util={r['utilization_pct']}, wall={r['wall_time_sec']:.1f}s")
        results.append(r)

    # Save runs.jsonl
    runs_path = RUN_DIR / "runs.jsonl"
    with open(runs_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Pick best candidate
    valid_results = [r for r in results if r["valid"] == True and r["placed_count"] == 276 and r["sheets_used"] is not None]
    if not valid_results:
        # Fall back to best by placed/sheets
        valid_results = sorted(
            [r for r in results if r["placed_count"] is not None],
            key=lambda x: (-(x["placed_count"] or 0), x.get("sheets_used", 999), -(x.get("utilization_pct") or 0), x.get("wall_time_sec", 999)),
        )

    best = valid_results[0] if valid_results else results[0]
    print(f"\nBest candidate: {best['label']} — placed={best['placed_count']}, sheets={best['sheets_used']}, util={best['utilization_pct']}, wall={best['wall_time_sec']:.1f}s")

    # Write best artifact
    with open(RUN_DIR / "best_candidate.json", "w") as f:
        with open(best["stdout_path"]) as src:
            f.write(src.read())
    shutil.copy(best["stdout_path"], RUN_DIR / "best_candidate.stdout.json")
    shutil.copy(best["stderr_path"], RUN_DIR / "best_candidate.stderr.log")

    print(f"\nResults saved to {RUN_DIR}")
    print(f"runs.jsonl: {runs_path}")
    print(f"best_candidate: {best['label']}")


if __name__ == "__main__":
    main()