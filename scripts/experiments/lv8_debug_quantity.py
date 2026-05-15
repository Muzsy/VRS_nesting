#!/usr/bin/env python3
"""Debug quantity handling in greedy_multi_sheet by checking the actual placement count."""

from __future__ import annotations

import json
import subprocess
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_BIN = REPO_ROOT / "rust" / "nesting_engine" / "target" / "release" / "nesting_engine"

# Small test: 3 instances of 2 part types
def make_test_input(quantity1: int, quantity2: int) -> dict:
    return {
        "version": "nesting_engine_v2",
        "seed": 42,
        "time_limit_sec": 60,
        "sheet": {
            "width_mm": 1000,
            "height_mm": 1000,
            "spacing_mm": 5,
            "margin_mm": 5,
            "kerf_mm": 0,
        },
        "parts": [
            {
                "id": "PART_A",
                "quantity": quantity1,
                "allowed_rotations_deg": [0],
                "outer_points_mm": [[0,0],[50,0],[50,50],[0,50]],
                "holes_points_mm": [],
            },
            {
                "id": "PART_B",
                "quantity": quantity2,
                "allowed_rotations_deg": [0],
                "outer_points_mm": [[0,0],[30,0],[30,30],[0,30]],
                "holes_points_mm": [],
            },
        ],
    }

def run_test(name: str, input_data: dict, search_mode: str, sa_iters: int = 0, sa_seed: int = 42) -> dict:
    payload = json.dumps(input_data, separators=(",", ":"))
    cli_args = ["--placer", "blf", "--compaction", "slide"]
    env = os.environ.copy()
    env["NESTING_ENGINE_SA_DIAG"] = "1"

    if search_mode == "sa":
        cli_args += ["--search", "sa", "--sa-iters", str(sa_iters), "--sa-seed", str(sa_seed), "--sa-eval-budget-sec", "5"]

    proc = subprocess.run(
        [str(ENGINE_BIN), "nest"] + cli_args,
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
    )

    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except:
        out = {}

    result = {
        "name": name,
        "search": search_mode,
        "sa_iters": sa_iters,
        "seed": sa_seed,
        "placed": len(out.get("placements", [])),
        "unplaced": len(out.get("unplaced", [])),
        "sheets_used": out.get("sheets_used", 0),
        "status": out.get("status", "unknown"),
        "stdout": proc.stdout[:500],
    }

    # Parse stderr for eval info
    for line in proc.stderr.split("\n"):
        if "GREEDY_EVAL_DONE" in line:
            result["last_eval"] = line
        if "SA start parts=" in line:
            result["sa_parts"] = line

    return result

def main():
    print("=== Quantity handling diagnostic ===\n")

    # Test 1: no-search, quantity=3 and quantity=5
    results = []

    for q1, q2, label in [
        (3, 2, "nosearch_q3_q2"),
        (5, 5, "nosearch_q5_q5"),
    ]:
        inp = make_test_input(q1, q2)
        total_q = q1 + q2
        r = run_test(label, inp, "none")
        results.append(r)
        print(f"{label}: input_total={total_q}, placed={r['placed']}, unplaced={r['unplaced']}, sheets={r['sheets_used']}, status={r['status']}")
        if r.get('last_eval'):
            print(f"  eval: {r['last_eval']}")

    print()

    # Test 2: SA mode, same quantities
    for sa_iters in [4, 8]:
        for seed in [42, 1]:
            inp = make_test_input(3, 2)
            total_q = 5
            r = run_test(f"sa_i{sa_iters}_s{seed}", inp, "sa", sa_iters=sa_iters, sa_seed=seed)
            results.append(r)
            print(f"sa_i{sa_iters}_s{seed}: input_total={total_q}, placed={r['placed']}, unplaced={r['unplaced']}, sheets={r['sheets_used']}, status={r['status']}")
            if r.get('sa_parts'):
                print(f"  {r['sa_parts']}")
            if r.get('last_eval'):
                print(f"  eval: {r['last_eval']}")

    print("\n=== Summary ===")
    print(f"{'Name':30s} {'Input':>7s} {'Placed':>7s} {'Sheets':>7s} {'Status':>10s}")
    for r in results:
        total = r['name'].split('_')
        q_str = r['name'].split('_')[1] if len(r['name'].split('_')) > 1 else "?"
        print(f"{r['name']:30s} {q_str:>7s} {r['placed']:>7d} {r['sheets_used']:>7d} {r['status']:>10s}")

if __name__ == "__main__":
    main()