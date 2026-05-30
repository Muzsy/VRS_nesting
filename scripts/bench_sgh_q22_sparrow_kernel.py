#!/usr/bin/env python3
"""SGH-Q22 Sparrow benchmark — local Hermes-friendly metrics run.

Matrix (default `--quick`):
  seeds: 1, 2, 3
  backends: bbox, cde (skipped if returns unsupported)
  fixtures: medium_10_to_20_items, synthetic_30_items
  pipelines: phase_optimizer vs sparrow_experimental

Outputs:
  codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json
  codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md

The benchmark is intentionally honest — if a configuration is slower or fails
to converge, it is reported as such. The PASS criterion for the canvas is
"real evidence about feasibility rate, runtime, query counts, and loss
reduction" — not beating any prior result.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BINARY = REPO_ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"
REPORT_DIR = REPO_ROOT / "codex" / "reports" / "egyedi_solver"


FIXTURES = {
    "medium_10_to_20_items": {
        "stocks": [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        "rotation_policy": "orthogonal",
        "time_limit_s": 5,
    },
    "synthetic_30_items": {
        "stocks": [{"id": "S", "quantity": 3, "width": 200.0, "height": 200.0}],
        "parts": [
            {"id": "A", "width": 30.0, "height": 20.0, "quantity": 15},
            {"id": "B", "width": 25.0, "height": 25.0, "quantity": 15},
        ],
        "rotation_policy": "orthogonal",
        "time_limit_s": 6,
    },
}

PIPELINES = ["phase_optimizer", "sparrow_experimental"]


def run_solver(input_dict: dict, hard_timeout_s: float = 30.0) -> tuple[dict, float]:
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "in.json"
        out_path = Path(tmpdir) / "out.json"
        in_path.write_text(json.dumps(input_dict))
        t0 = time.perf_counter()
        try:
            result = subprocess.run(
                [str(BINARY), "--input", str(in_path), "--output", str(out_path)],
                capture_output=True, text=True, timeout=hard_timeout_s,
            )
        except subprocess.TimeoutExpired:
            runtime_ms = (time.perf_counter() - t0) * 1000.0
            return ({"_error": f"timeout after {hard_timeout_s}s",
                     "status": "timeout"}, runtime_ms)
        runtime_ms = (time.perf_counter() - t0) * 1000.0
        if result.returncode != 0:
            return ({"_error": result.stderr[:200]}, runtime_ms)
        return (json.loads(out_path.read_text()), runtime_ms)


def build_input(fixture_name: str, pipeline: str, backend: str, seed: int) -> dict:
    f = FIXTURES[fixture_name]
    return {
        "contract_version": "v1",
        "project_name": f"q22_bench_{fixture_name}",
        "seed": seed,
        "time_limit_s": f["time_limit_s"],
        "solver_profile": PROFILE,
        "optimizer_pipeline": pipeline,
        "rotation_policy": f["rotation_policy"],
        "collision_backend": backend,
        "stocks": f["stocks"],
        "parts": f["parts"],
    }


def summarize_run(out: dict, runtime_ms: float) -> dict:
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    metrics = out.get("metrics", {})
    return {
        "status": out.get("status", "?"),
        "runtime_ms": round(runtime_ms, 1),
        "placed_count": metrics.get("placed_count"),
        "unplaced_count": metrics.get("unplaced_count"),
        "pipeline_used": od.get("pipeline_used"),
        # Sparrow fields (None for phase_optimizer)
        "sparrow_converged": od.get("sparrow_converged"),
        "sparrow_iterations": od.get("sparrow_iterations"),
        "sparrow_moves_attempted": od.get("sparrow_moves_attempted"),
        "sparrow_moves_accepted": od.get("sparrow_moves_accepted"),
        "sparrow_rollbacks": od.get("sparrow_rollbacks"),
        "sparrow_initial_raw_loss": od.get("sparrow_initial_raw_loss"),
        "sparrow_final_raw_loss": od.get("sparrow_final_raw_loss"),
        "sparrow_collision_graph_initial_pairs": od.get("sparrow_collision_graph_initial_pairs"),
        "sparrow_collision_graph_final_pairs": od.get("sparrow_collision_graph_final_pairs"),
        "sparrow_search_position_calls": od.get("sparrow_search_position_calls"),
        # Backend diag
        "backend_used": cbd.get("backend_used"),
        "bbox_fallback_queries": cbd.get("bbox_fallback_queries"),
        "cde_total_queries": cbd.get("cde_total_queries"),
        # Phase optimizer fields for comparison
        "phase_optimizer_invoked": od.get("phase_optimizer_invoked"),
        "exploration_iterations": od.get("exploration_iterations"),
        "compression_iterations": od.get("compression_iterations"),
    }


def emit_md(results: dict) -> str:
    lines = []
    lines.append("# SGH-Q22 Sparrow benchmark measurements\n")
    lines.append("Quick local matrix run. Each row = (fixture, pipeline, backend, seed) → metrics.\n")
    lines.append("| fixture | pipeline | backend | seed | status | placed | runtime_ms | sp_init_raw | sp_final_raw | sp_iters | sp_moves | sp_pairs_i→f | bbox_fb | cde_total |")
    lines.append("|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|")
    for row in results["rows"]:
        m = row["metrics"]
        pairs_arrow = (
            f"{m.get('sparrow_collision_graph_initial_pairs') or '-'}→"
            f"{m.get('sparrow_collision_graph_final_pairs') or '-'}"
        )
        lines.append(
            f"| {row['fixture']} | {row['pipeline']} | {row['backend']} | {row['seed']} | "
            f"{m['status']} | {m['placed_count'] or '-'} | {m['runtime_ms']} | "
            f"{m.get('sparrow_initial_raw_loss') or '-'} | "
            f"{m.get('sparrow_final_raw_loss') or '-'} | "
            f"{m.get('sparrow_iterations') or '-'} | "
            f"{m.get('sparrow_moves_accepted') or '-'} / "
            f"{m.get('sparrow_moves_attempted') or '-'} | "
            f"{pairs_arrow} | "
            f"{m.get('bbox_fallback_queries') if m.get('bbox_fallback_queries') is not None else '-'} | "
            f"{m.get('cde_total_queries') or '-'} |"
        )
    lines.append("")
    lines.append("## Summary\n")
    lines.append(f"- Configurations run: **{len(results['rows'])}**")
    lines.append(f"- Sparrow runs converged: **{results['sparrow_converged_count']} / {results['sparrow_total']}**")
    lines.append(f"- Total runtime: **{results['total_runtime_ms']:.0f} ms**")
    if results.get("notes"):
        lines.append("\n### Notes\n")
        for n in results["notes"]:
            lines.append(f"- {n}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="SGH-Q22 sparrow benchmark")
    ap.add_argument("--quick", action="store_true",
                    help="Quick mode: 3 seeds × small fixtures (default)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    args = ap.parse_args()

    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)

    seeds = args.seeds
    backends = ["bbox", "cde"]

    rows = []
    sparrow_total = 0
    sparrow_converged_count = 0
    total_runtime_ms = 0.0
    notes = []

    for fixture_name in FIXTURES:
        for pipeline in PIPELINES:
            for backend in backends:
                for seed in seeds:
                    print(f"[run] fixture={fixture_name} pipeline={pipeline} "
                          f"backend={backend} seed={seed}", flush=True)
                    inp = build_input(fixture_name, pipeline, backend, seed)
                    out, ms = run_solver(inp)
                    total_runtime_ms += ms
                    metrics = summarize_run(out, ms)
                    if pipeline == "sparrow_experimental" and metrics["status"] != "unsupported":
                        sparrow_total += 1
                        if metrics.get("sparrow_converged"):
                            sparrow_converged_count += 1
                    if "_error" in out:
                        notes.append(
                            f"{fixture_name}/{pipeline}/{backend}/seed={seed} solver error: {out['_error']}"
                        )
                    rows.append({
                        "fixture": fixture_name,
                        "pipeline": pipeline,
                        "backend": backend,
                        "seed": seed,
                        "metrics": metrics,
                    })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "sgh_q22_sparrow_state_separation_kernel_measurements.json"
    md_path = REPORT_DIR / "sgh_q22_sparrow_state_separation_kernel_measurements.md"
    results = {
        "rows": rows,
        "sparrow_total": sparrow_total,
        "sparrow_converged_count": sparrow_converged_count,
        "total_runtime_ms": total_runtime_ms,
        "notes": notes,
    }
    json_path.write_text(json.dumps(results, indent=2))
    md_path.write_text(emit_md(results))
    print(f"\n[done] wrote {json_path}")
    print(f"[done] wrote {md_path}")
    print(f"sparrow_converged_count / sparrow_total = {sparrow_converged_count}/{sparrow_total}")


if __name__ == "__main__":
    main()
