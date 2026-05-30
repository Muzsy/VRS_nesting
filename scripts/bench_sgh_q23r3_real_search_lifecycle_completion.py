#!/usr/bin/env python3
"""SGH-Q23R3 real Sparrow search lifecycle completion benchmark.

Adds single-engine multi-hazard batch metrics (cde_batch_engine_builds,
cde_batch_candidate_queries, total engine builds, pairwise fallback) to track the
>=80% engine-build reduction vs the Q23 baseline (7650).

Adds solve-scoped CDE cache metrics (hits/misses, prepared, invalidations) to the
Q23 matrix and tracks engine-build reduction vs the Q23 baseline (7650).

Matrix (`--quick`):
  pipelines:
    sparrow_cde            (production — acceptance)
    sparrow_experimental   (previous path — comparison only)
    phase_optimizer        (legacy comparison — NOT acceptance)
  backends:
    cde                    (production geometry truth)
    bbox                   (debug comparison only, for phase_optimizer)
  fixtures:
    tiny, two_rect_overlap, boundary_recovery, medium_10_to_20_items
    synthetic_30_items     (full mode only — may timeout under quick cap)
  seeds: [1] quick / [1,2,3] full

Honest accounting: EVERY production `sparrow_cde` run counts in the denominator,
including ok / partial / unsupported / timeout / error. Zero/false values render
as `0`/`false`; only missing fields render as `-`.

Outputs:
  codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.json
  codex/reports/egyedi_solver/sgh_q23_full_sparrow_parity_cutover_measurements.md
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BINARY = REPO_ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
PROFILE = "jagua_optimizer_phase1_outer_only"
REPORT_DIR = REPO_ROOT / "codex" / "reports" / "egyedi_solver"
STEM = "sgh_q23r3_real_search_lifecycle_measurements"
LV8_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nesting_engine" / "ne2_input_lv8jav.json"

FIXTURES = {
    "tiny": {
        "stocks": [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}],
        "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 2}],
        "rotation_policy": "orthogonal", "time_limit_s": 5, "required": 2,
    },
    "two_rect_overlap": {
        "stocks": [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}],
        "parts": [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 2}],
        "rotation_policy": "orthogonal", "time_limit_s": 5, "required": 2,
    },
    "boundary_recovery": {
        "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
        "parts": [{"id": "P", "width": 40.0, "height": 30.0, "quantity": 1}],
        "rotation_policy": "orthogonal", "time_limit_s": 5, "required": 1,
    },
    "medium_10_to_20_items": {
        "stocks": [{"id": "S", "quantity": 2, "width": 200.0, "height": 200.0}],
        "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 12}],
        "rotation_policy": "orthogonal", "time_limit_s": 8, "required": 12,
    },
    "synthetic_30_items": {
        "stocks": [{"id": "S", "quantity": 3, "width": 200.0, "height": 200.0}],
        "parts": [
            {"id": "A", "width": 30.0, "height": 20.0, "quantity": 15},
            {"id": "B", "width": 25.0, "height": 25.0, "quantity": 15},
        ],
        "rotation_policy": "orthogonal", "time_limit_s": 10, "required": 30,
    },
}

# (pipeline, backend, role). role: "production" counts towards acceptance denom.
CONFIGS = [
    ("sparrow_cde", "cde", "production"),
    ("sparrow_experimental", "cde", "comparison"),
    ("phase_optimizer", "bbox", "comparison"),
]

QUICK_FIXTURES = ["tiny", "two_rect_overlap", "boundary_recovery", "medium_10_to_20_items"]


def maybe_add_lv8_subset():
    if not LV8_FIXTURE.exists() or "lv8_subset" in FIXTURES:
        return
    data = json.loads(LV8_FIXTURE.read_text())
    sheet = data.get("sheet") or {}
    parts = []
    for part in data.get("parts", []):
        if part.get("holes_points_mm"):
            continue
        pts = part.get("outer_points_mm") or []
        if not pts:
            continue
        xs = [float(pt[0]) for pt in pts]
        ys = [float(pt[1]) for pt in pts]
        p = {
            "id": part["id"],
            "quantity": 1,
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
            "allowed_rotations_deg": part.get("allowed_rotations_deg", [0, 90, 180, 270]),
            "outer_points": pts,
        }
        parts.append(p)
        if len(parts) >= 12:
            break
    if not parts:
        return
    FIXTURES["lv8_subset"] = {
        "stocks": [{
            "id": "LV8_SHEET",
            "quantity": 1,
            "width": float(sheet.get("width_mm", 1500.0)),
            "height": float(sheet.get("height_mm", 3000.0)),
        }],
        "parts": parts,
        "rotation_policy": data.get("rotation_policy", "orthogonal"),
        "time_limit_s": min(int(data.get("time_limit_s", 8) or 8), 8),
        "required": sum(int(p.get("quantity", 0)) for p in parts),
    }
    QUICK_FIXTURES.append("lv8_subset")


def run_solver(input_dict: dict, hard_timeout_s: float = 35.0) -> tuple[dict, float]:
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
            return ({"_error": f"timeout after {hard_timeout_s}s", "status": "timeout"},
                    (time.perf_counter() - t0) * 1000.0)
        runtime_ms = (time.perf_counter() - t0) * 1000.0
        if result.returncode != 0:
            return ({"_error": result.stderr[:200], "status": "error"}, runtime_ms)
        return (json.loads(out_path.read_text()), runtime_ms)


def build_input(fixture_name: str, pipeline: str, backend: str, seed: int) -> dict:
    f = FIXTURES[fixture_name]
    return {
        "contract_version": "v1",
        "project_name": f"q23_bench_{fixture_name}",
        "seed": seed,
        "time_limit_s": f["time_limit_s"],
        "solver_profile": PROFILE,
        "optimizer_pipeline": pipeline,
        "rotation_policy": f["rotation_policy"],
        "collision_backend": backend,
        "stocks": f["stocks"],
        "parts": f["parts"],
    }


def summarize(out: dict, runtime_ms: float, required: int) -> dict:
    od = out.get("optimizer_diagnostics") or {}
    cbd = out.get("collision_backend_diagnostics") or {}
    metrics = out.get("metrics", {})
    return {
        "status": out.get("status", "?"),
        "runtime_ms": round(runtime_ms, 1),
        "placed_count": metrics.get("placed_count"),
        "required_count": required,
        "pipeline_used": od.get("pipeline_used"),
        "sparrow_converged": od.get("sparrow_converged"),
        "sparrow_iterations": od.get("sparrow_iterations"),
        "sparrow_moves_attempted": od.get("sparrow_moves_attempted"),
        "sparrow_moves_accepted": od.get("sparrow_moves_accepted"),
        "sparrow_rollbacks": od.get("sparrow_rollbacks"),
        "sparrow_gls_weight_updates": od.get("sparrow_gls_weight_updates"),
        "sparrow_initial_raw_loss": od.get("sparrow_initial_raw_loss"),
        "sparrow_final_raw_loss": od.get("sparrow_final_raw_loss"),
        "sparrow_best_infeasible_raw_loss": od.get("sparrow_best_infeasible_raw_loss"),
        "collision_pairs_initial": od.get("sparrow_collision_graph_initial_pairs"),
        "collision_pairs_final": od.get("sparrow_collision_graph_final_pairs"),
        "search_position_calls": od.get("sparrow_search_position_calls"),
        "search_position_samples": od.get("sparrow_search_position_samples"),
        "lbf_fallback_used": od.get("search_position_lbf_fallback_used"),
        "backend_used": cbd.get("backend_used"),
        "bbox_fallback_queries": cbd.get("bbox_fallback_queries"),
        "cde_total_queries": cbd.get("cde_total_queries"),
        "cde_pair_queries": cbd.get("cde_pair_queries"),
        "cde_boundary_queries": cbd.get("cde_boundary_queries"),
        "cde_engine_builds": cbd.get("cde_engine_builds"),
        "cde_broadphase_pruned": cbd.get("cde_broadphase_pruned"),
        "cde_cache_pair_hits": cbd.get("cde_cache_pair_hits"),
        "cde_cache_pair_misses": cbd.get("cde_cache_pair_misses"),
        "cde_cache_prepared_hits": cbd.get("cde_cache_prepared_hits"),
        "cde_cache_boundary_hits": cbd.get("cde_cache_boundary_hits"),
        "cde_cache_invalidations": cbd.get("cde_cache_invalidations"),
        "cde_batch_engine_builds": cbd.get("cde_batch_engine_builds"),
        "cde_batch_candidate_queries": cbd.get("cde_batch_candidate_queries"),
        "cde_batch_hazards_registered": cbd.get("cde_batch_hazards_registered"),
        "cde_pairwise_fallback_queries": cbd.get("cde_pairwise_fallback_queries"),
        "total_engine_builds": (cbd.get("cde_engine_builds") or 0) + (cbd.get("cde_batch_engine_builds") or 0),
        "sparrow_workers": od.get("sparrow_workers"),
        "sparrow_worker_passes": od.get("sparrow_worker_passes"),
        "sparrow_worker_candidates_evaluated": od.get("sparrow_worker_candidates_evaluated"),
        "sparrow_worker_commits": od.get("sparrow_worker_commits"),
        "sparrow_worker_rollbacks": od.get("sparrow_worker_rollbacks"),
        "sparrow_multi_target_items_attempted": od.get("sparrow_multi_target_items_attempted"),
        "sparrow_topk_target_count": od.get("sparrow_topk_target_count"),
        "sparrow_graph_full_rebuilds": od.get("sparrow_graph_full_rebuilds"),
        "sparrow_graph_incremental_updates": od.get("sparrow_graph_incremental_updates"),
        "sparrow_graph_edges_recomputed": od.get("sparrow_graph_edges_recomputed"),
        "sparrow_graph_debug_rebuild_mismatches": od.get("sparrow_graph_debug_rebuild_mismatches"),
        "sparrow_exploration_restarts": od.get("sparrow_exploration_restarts"),
        "sparrow_exploration_seed_strategies": od.get("sparrow_exploration_seed_strategies"),
        "sparrow_exploration_disruptions": od.get("sparrow_exploration_disruptions"),
        "sparrow_exploration_best_feasible_found": od.get("sparrow_exploration_best_feasible_found"),
        "sparrow_compression_passes": od.get("sparrow_compression_passes"),
        "sparrow_compression_candidates_evaluated": od.get("sparrow_compression_candidates_evaluated"),
        "sparrow_fixed_sheet_objective_before": od.get("sparrow_fixed_sheet_objective_before"),
        "sparrow_fixed_sheet_objective_after": od.get("sparrow_fixed_sheet_objective_after"),
        "error": out.get("_error"),
    }


def render_value(v):
    """Only None → '-'. 0 / 0.0 / False / '' render as themselves."""
    return "-" if v is None else v


def emit_md(results: dict) -> str:
    L = []
    L.append("# SGH-Q23R3 real Sparrow search lifecycle completion — benchmark measurements\n")
    L.append("Production path = `sparrow_cde` (CDE-first). `sparrow_experimental` and "
             "`phase_optimizer` are comparison-only, not acceptance.\n")
    L.append("**Accounting:** every production `sparrow_cde` run counts in the denominator "
             "(ok / partial / unsupported / timeout / error). Zero/false render as themselves; "
             "only missing fields as `-`.\n")
    L.append("| fixture | pipeline | backend | seed | status | placed/req | runtime_ms | conv | iters | "
             "moves a/att | pairs i->f | raw i->f | workers | topk | graph incr/full | restarts | compression | cde_q | engine_builds | bbox_fb | lbf_fb |")
    L.append("|---|---|---|---:|---|---|---:|---|---:|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|")
    for row in results["rows"]:
        m = row["metrics"]
        pairs = f"{render_value(m.get('collision_pairs_initial'))}→{render_value(m.get('collision_pairs_final'))}"
        raw = f"{render_value(m.get('sparrow_initial_raw_loss'))}→{render_value(m.get('sparrow_final_raw_loss'))}"
        placed = f"{render_value(m.get('placed_count'))}/{m.get('required_count')}"
        moves = f"{render_value(m.get('sparrow_moves_accepted'))}/{render_value(m.get('sparrow_moves_attempted'))}"
        L.append(
            f"| {row['fixture']} | {row['pipeline']} | {row['backend']} | {row['seed']} | "
            f"{m['status']} | {placed} | {m['runtime_ms']} | {render_value(m.get('sparrow_converged'))} | "
            f"{render_value(m.get('sparrow_iterations'))} | {moves} | {pairs} | {raw} | "
            f"{render_value(m.get('sparrow_workers'))} | {render_value(m.get('sparrow_topk_target_count'))} | "
            f"{render_value(m.get('sparrow_graph_incremental_updates'))}/{render_value(m.get('sparrow_graph_full_rebuilds'))} | "
            f"{render_value(m.get('sparrow_exploration_restarts'))} | {render_value(m.get('sparrow_compression_passes'))} | "
            f"{render_value(m.get('cde_total_queries'))} | {render_value(m.get('total_engine_builds'))} | "
            f"{render_value(m.get('bbox_fallback_queries'))} | "
            f"{render_value(m.get('lbf_fallback_used'))} |"
        )
    L.append("")
    L.append("## Production (`sparrow_cde`) outcome accounting\n")
    pa = results["production_accounting"]
    L.append("| outcome | count |")
    L.append("|---|---:|")
    for k in ("ok", "partial", "unsupported", "timeout", "error"):
        L.append(f"| {k} | {pa.get(k, 0)} |")
    L.append(f"| **total** | **{pa['total']}** |")
    L.append(f"| **converged** | **{pa['converged']}** |")
    L.append("")
    if results.get("notes"):
        L.append("## Notes\n")
        for n in results["notes"]:
            L.append(f"- {n}")
    L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="SGH-Q23 sparrow cutover benchmark")
    ap.add_argument("--quick", action="store_true", help="quick matrix (1 seed, no synthetic_30)")
    ap.add_argument("--seeds", type=int, nargs="+", default=None)
    args = ap.parse_args()

    if not BINARY.exists():
        print(f"ERROR: binary not found at {BINARY}")
        sys.exit(1)

    maybe_add_lv8_subset()

    if args.quick:
        fixtures = QUICK_FIXTURES
        seeds = args.seeds or [1]
    else:
        fixtures = list(FIXTURES.keys())
        seeds = args.seeds or [1, 2, 3]

    rows = []
    notes = []
    production_accounting = {"ok": 0, "partial": 0, "unsupported": 0,
                             "timeout": 0, "error": 0, "total": 0, "converged": 0}
    total_runtime_ms = 0.0

    for fixture_name in fixtures:
        required = FIXTURES[fixture_name]["required"]
        for pipeline, backend, role in CONFIGS:
            for seed in seeds:
                print(f"[run] {fixture_name} {pipeline}/{backend} seed={seed} ({role})", flush=True)
                inp = build_input(fixture_name, pipeline, backend, seed)
                hard_timeout = 35.0
                if fixture_name == "lv8_subset":
                    inp["seed"] = 11
                    hard_timeout = 60.0
                out, ms = run_solver(inp, hard_timeout_s=hard_timeout)
                total_runtime_ms += ms
                m = summarize(out, ms, required)
                if role == "production":
                    production_accounting["total"] += 1
                    st = m["status"] if m["status"] in production_accounting else "error"
                    production_accounting[st] = production_accounting.get(st, 0) + 1
                    if m.get("sparrow_converged") is True:
                        production_accounting["converged"] += 1
                if m.get("error"):
                    notes.append(f"{fixture_name}/{pipeline}/{backend}/seed={seed}: {m['error']}")
                rows.append({"fixture": fixture_name, "pipeline": pipeline,
                             "backend": backend, "role": role, "seed": seed, "metrics": m})

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = {
        "rows": rows,
        "production_accounting": production_accounting,
        "total_runtime_ms": total_runtime_ms,
        "notes": notes,
    }
    (REPORT_DIR / f"{STEM}.json").write_text(json.dumps(results, indent=2))
    (REPORT_DIR / f"{STEM}.md").write_text(emit_md(results))
    print(f"\n[done] wrote {REPORT_DIR / (STEM + '.json')}")
    print(f"[done] wrote {REPORT_DIR / (STEM + '.md')}")
    print(f"production converged/total = {production_accounting['converged']}/{production_accounting['total']}")


if __name__ == "__main__":
    main()
