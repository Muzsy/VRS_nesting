#!/usr/bin/env python3
"""SGH-Q44 - Per-attempt multisheet timing and CDE diagnostics extractor.

This is a DIAGNOSTIC / instrumentation extractor, not a solver-strategy task. It does
NOT change any solver behaviour. It reads the Q42 solver output JSONs (which, after the
SGH-Q44 instrumentation, carry
`optimizer_diagnostics.sparrow_ms_attempt_diagnostics`), and produces the per-attempt
evidence tables required by the Q44 report:

  1. Baseline confirmation (aggregate values vs the Q42 baseline).
  2. Candidate subset schedule (allocated vs actual time per attempt).
  3. Attempt outcome table (placed / unplaced / pairs / incumbent / stop reason).
  4. Attempt-level CDE cost table (per-attempt CDE counter deltas + % split).
  5. Attempt-level Sparrow/search cost table.
  6. 1200s vs 2400s delta analysis (which attempt received the extra runtime).
  7. Stop-reason analysis.

It also CHECKS that the per-attempt CDE deltas sum to the aggregate
`collision_backend_diagnostics` counters and reports the (small) post-loop residual.

By default it reads the existing Q42 outputs. With `--run` it (re)invokes the solver on
the canonical Q42 inputs first (long: 1200 s + 2400 s).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"

Q42 = ROOT / "artifacts/benchmarks/sgh_q42"
Q42_INPUTS = Q42 / "inputs"
Q42_OUTPUTS = Q42 / "outputs"
Q44 = ROOT / "artifacts/benchmarks/sgh_q44"

RUN_ID_PREFIX = "q42_full276_3x1500x3000_margin5_spacing8_continuous"
RUN_TIMES = [1200, 2400]

# Q42 baseline aggregates (from the task spec / committed Q42 artifacts) used for the
# "baseline confirmation" section. None where the baseline only gives an approximate value.
Q42_BASELINE = {
    1200: {
        "placed_count": 276,
        "unplaced_count": 0,
        "used_sheet_count": 3,
        "sparrow_ms_attempts": 3,
        "sparrow_ms_candidate_subsets": 3,
        "sparrow_ms_runtime_ms": 706582.953092,
        "cde_engine_builds": 33932,
        "cde_batch_candidate_queries": 5132793,
        "cde_batch_engine_builds": 98360,
        "cde_batch_hazards_registered": 3762730,
        "cde_batch_collisions_returned": 9226973,
    },
    2400: {
        "placed_count": 276,
        "unplaced_count": 0,
        "used_sheet_count": 3,
        "sparrow_ms_attempts": 3,
        "sparrow_ms_candidate_subsets": 3,
        "sparrow_ms_runtime_ms": 1305567.990552,
        "cde_engine_builds": 58762,
        "cde_batch_candidate_queries": 8219721,
        "cde_batch_engine_builds": 190704,
        "cde_batch_hazards_registered": 7544586,
        "cde_batch_collisions_returned": 16527771,
    },
}

# CDE counters that are attributed per-attempt by the instrumentation. The aggregate
# counter name (in collision_backend_diagnostics) maps to the per-attempt delta field.
CDE_COUNTERS = [
    ("cde_engine_builds", "cde_engine_builds_delta"),
    ("cde_batch_candidate_queries", "cde_batch_candidate_queries_delta"),
    ("cde_batch_engine_builds", "cde_batch_engine_builds_delta"),
    ("cde_batch_hazards_registered", "cde_batch_hazards_registered_delta"),
    ("cde_batch_collisions_returned", "cde_batch_collisions_returned_delta"),
    ("cde_candidate_session_builds", "cde_candidate_session_builds_delta"),
    ("cde_candidate_session_reuses", "cde_candidate_session_reuses_delta"),
]


def output_path(time_limit_s: int) -> Path:
    return Q42_OUTPUTS / f"{RUN_ID_PREFIX}_{time_limit_s}_output.json"


def input_path(time_limit_s: int) -> Path:
    return Q42_INPUTS / f"{RUN_ID_PREFIX}_{time_limit_s}.json"


def run_solver(time_limit_s: int) -> None:
    out = output_path(time_limit_s)
    inp = input_path(time_limit_s)
    if not inp.exists():
        raise SystemExit(f"missing Q42 input (run bench_sgh_q42 first): {inp}")
    env = dict(os.environ)
    env.pop("SGH_Q35_SPACING_VALIDATOR", None)
    t0 = time.monotonic()
    proc = subprocess.run(
        [str(SOLVER_BIN), "--input", str(inp), "--output", str(out)],
        capture_output=True, text=True, timeout=time_limit_s + 1800, env=env,
    )
    wall = time.monotonic() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"solver exit {proc.returncode}: {proc.stderr[:800]}")
    print(f"  ran {time_limit_s}s solve: wall={wall:.1f}s")


def load_output(time_limit_s: int) -> dict[str, Any] | None:
    p = output_path(time_limit_s)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def od(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("optimizer_diagnostics") or {}


def cbd(out: dict[str, Any]) -> dict[str, Any]:
    return out.get("collision_backend_diagnostics") or {}


def pct(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 2) if whole else 0.0


def attempt_rows(out: dict[str, Any]) -> list[dict[str, Any]]:
    return od(out).get("sparrow_ms_attempt_diagnostics") or []


def baseline_confirmation(time_limit_s: int, out: dict[str, Any]) -> dict[str, Any]:
    d, c = od(out), cbd(out)
    m = out.get("metrics", {})
    base = Q42_BASELINE.get(time_limit_s, {})
    row = {
        "run_id": f"{RUN_ID_PREFIX}_{time_limit_s}",
        "time_limit_s": time_limit_s,
        "status": out.get("status"),
        "placed_count": int(m.get("placed_count", 0)),
        "unplaced_count": int(m.get("unplaced_count", 0)),
        "used_sheet_count": d.get("sparrow_ms_used_sheet_count"),
        "sparrow_ms_attempts": d.get("sparrow_ms_attempts"),
        "sparrow_ms_candidate_subsets": d.get("sparrow_ms_candidate_subsets"),
        "sparrow_ms_runtime_ms": d.get("sparrow_ms_runtime_ms"),
        "wall_time_s": out.get("_wall_time_s"),
        "cde_engine_builds": c.get("cde_engine_builds"),
        "cde_batch_candidate_queries": c.get("cde_batch_candidate_queries"),
        "cde_batch_engine_builds": c.get("cde_batch_engine_builds"),
        "cde_batch_hazards_registered": c.get("cde_batch_hazards_registered"),
        "cde_batch_collisions_returned": c.get("cde_batch_collisions_returned"),
        "attempt_diagnostics_count": d.get("sparrow_ms_attempt_diagnostics_count"),
        "attempt_diagnostics_schema_version": d.get("sparrow_ms_attempt_diagnostics_schema_version"),
    }
    # delta vs baseline for the headline counters
    row["_baseline"] = base
    return row


def consistency_check(out: dict[str, Any]) -> dict[str, Any]:
    """Per-attempt CDE deltas must sum to the aggregate counters; the residual is the
    post-loop margin/spacing validator work (which does not touch CDE batch counters)."""
    rows = attempt_rows(out)
    c = cbd(out)
    result = {}
    for agg_name, delta_field in CDE_COUNTERS:
        agg = c.get(agg_name)
        s = sum(int(r.get(delta_field, 0)) for r in rows)
        result[agg_name] = {
            "aggregate": agg,
            "sum_of_attempt_deltas": s,
            "residual": (agg - s) if isinstance(agg, int) else None,
        }
    return result


def schedule_table(out: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for a in attempt_rows(out):
        rows.append({
            "attempt_index": a.get("attempt_index"),
            "subset_indices_original": a.get("subset_indices_original"),
            "subset_size": a.get("subset_size"),
            "subset_signature": a.get("subset_signature"),
            "is_full_pool": a.get("is_full_pool"),
            "is_second_to_last": a.get("is_second_to_last"),
            "allocated_time_limit_s": round(a.get("allocated_time_limit_s", 0.0), 2),
            "actual_runtime_ms": round(a.get("actual_runtime_ms", 0.0), 1),
            "actual_runtime_s": round(a.get("actual_runtime_ms", 0.0) / 1000.0, 1),
            "remaining_budget_before_s": round(a.get("remaining_budget_before_s", 0.0), 1),
            "remaining_budget_after_s": round(a.get("remaining_budget_after_s", 0.0), 1),
            "deadline_hit_after_attempt": a.get("deadline_hit_after_attempt"),
        })
    return rows


def outcome_table(out: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for a in attempt_rows(out):
        rows.append({
            "attempt_index": a.get("attempt_index"),
            "core_feasible": a.get("core_feasible"),
            "core_status": a.get("core_status"),
            "placed_after_sanitize": a.get("placed_after_sanitize"),
            "unplaced_after_sanitize": a.get("unplaced_after_sanitize"),
            "used_sheet_count": a.get("used_sheet_count"),
            "used_sheet_indices_original": a.get("used_sheet_indices_original"),
            "final_pairs": a.get("sparrow_collision_graph_final_pairs"),
            "boundary_violations": a.get("sparrow_boundary_violations_final"),
            "sanitized": a.get("sanitized"),
            "candidate_score": a.get("candidate_score"),
            "became_incumbent": a.get("became_incumbent"),
            "incumbent_reason": a.get("incumbent_reason"),
            "stop_reason": a.get("stop_reason"),
        })
    return rows


def cde_cost_table(out: dict[str, Any]) -> list[dict[str, Any]]:
    rows = attempt_rows(out)
    tot_rt = sum(r.get("actual_runtime_ms", 0.0) for r in rows) or 1.0
    tot_q = sum(r.get("cde_batch_candidate_queries_delta", 0) for r in rows) or 1
    tot_beb = sum(r.get("cde_batch_engine_builds_delta", 0) for r in rows) or 1
    tot_haz = sum(r.get("cde_batch_hazards_registered_delta", 0) for r in rows) or 1
    tot_col = sum(r.get("cde_batch_collisions_returned_delta", 0) for r in rows) or 1
    table = []
    for a in rows:
        table.append({
            "attempt_index": a.get("attempt_index"),
            "subset_size": a.get("subset_size"),
            "actual_runtime_ms": round(a.get("actual_runtime_ms", 0.0), 1),
            "cde_engine_builds_delta": a.get("cde_engine_builds_delta"),
            "cde_batch_candidate_queries_delta": a.get("cde_batch_candidate_queries_delta"),
            "cde_batch_engine_builds_delta": a.get("cde_batch_engine_builds_delta"),
            "cde_batch_hazards_registered_delta": a.get("cde_batch_hazards_registered_delta"),
            "cde_batch_collisions_returned_delta": a.get("cde_batch_collisions_returned_delta"),
            "cde_candidate_session_builds_delta": a.get("cde_candidate_session_builds_delta"),
            "cde_candidate_session_reuses_delta": a.get("cde_candidate_session_reuses_delta"),
            "attempt_runtime_pct": pct(a.get("actual_runtime_ms", 0.0), tot_rt),
            "candidate_query_pct": pct(a.get("cde_batch_candidate_queries_delta", 0), tot_q),
            "batch_engine_build_pct": pct(a.get("cde_batch_engine_builds_delta", 0), tot_beb),
            "hazard_registered_pct": pct(a.get("cde_batch_hazards_registered_delta", 0), tot_haz),
            "collisions_returned_pct": pct(a.get("cde_batch_collisions_returned_delta", 0), tot_col),
        })
    return table


def sparrow_cost_table(out: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for a in attempt_rows(out):
        rows.append({
            "attempt_index": a.get("attempt_index"),
            "sparrow_iterations": a.get("sparrow_iterations"),
            "sparrow_moves_attempted": a.get("sparrow_moves_attempted"),
            "sparrow_moves_accepted": a.get("sparrow_moves_accepted"),
            "sparrow_rollbacks": a.get("sparrow_rollbacks"),
            "sparrow_search_position_calls": a.get("sparrow_search_position_calls"),
            "sparrow_search_position_samples": a.get("sparrow_search_position_samples"),
            "search_position_coord_descent_steps": a.get("search_position_coord_descent_steps"),
            "sparrow_graph_edges_recomputed": a.get("sparrow_graph_edges_recomputed"),
            "sparrow_graph_full_rebuilds": a.get("sparrow_graph_full_rebuilds"),
            "sparrow_graph_incremental_updates": a.get("sparrow_graph_incremental_updates"),
        })
    return rows


def delta_analysis(out_a: dict[str, Any], out_b: dict[str, Any]) -> dict[str, Any]:
    """1200 -> 2400 delta per headline metric, and which attempt received most of it."""
    rows_a = attempt_rows(out_a)
    rows_b = attempt_rows(out_b)
    c_a, c_b = cbd(out_a), cbd(out_b)
    d_a, d_b = od(out_a), od(out_b)

    metrics = [
        ("sparrow_ms_runtime_ms", None, d_a.get("sparrow_ms_runtime_ms"), d_b.get("sparrow_ms_runtime_ms"), "actual_runtime_ms"),
        ("cde_batch_candidate_queries", "cde_batch_candidate_queries", c_a.get("cde_batch_candidate_queries"), c_b.get("cde_batch_candidate_queries"), "cde_batch_candidate_queries_delta"),
        ("cde_batch_engine_builds", "cde_batch_engine_builds", c_a.get("cde_batch_engine_builds"), c_b.get("cde_batch_engine_builds"), "cde_batch_engine_builds_delta"),
        ("cde_batch_hazards_registered", "cde_batch_hazards_registered", c_a.get("cde_batch_hazards_registered"), c_b.get("cde_batch_hazards_registered"), "cde_batch_hazards_registered_delta"),
        ("cde_batch_collisions_returned", "cde_batch_collisions_returned", c_a.get("cde_batch_collisions_returned"), c_b.get("cde_batch_collisions_returned"), "cde_batch_collisions_returned_delta"),
        ("cde_engine_builds", "cde_engine_builds", c_a.get("cde_engine_builds"), c_b.get("cde_engine_builds"), "cde_engine_builds_delta"),
    ]

    n = min(len(rows_a), len(rows_b))
    out = []
    for name, _agg, total_a, total_b, per_field in metrics:
        # per-attempt deltas (B - A) by attempt index, matched by subset_size where possible
        by_size_a = {r.get("subset_size"): r for r in rows_a}
        by_size_b = {r.get("subset_size"): r for r in rows_b}
        per_attempt_delta = {}
        for size in sorted(set(by_size_a) | set(by_size_b)):
            va = by_size_a.get(size, {}).get(per_field, 0) or 0
            vb = by_size_b.get(size, {}).get(per_field, 0) or 0
            per_attempt_delta[size] = vb - va
        # which subset (attempt) got the most delta
        if per_attempt_delta:
            top_size = max(per_attempt_delta, key=lambda s: per_attempt_delta[s])
            total_delta = (total_b - total_a) if (isinstance(total_a, (int, float)) and isinstance(total_b, (int, float))) else None
            top_delta = per_attempt_delta[top_size]
            delta_pct = pct(top_delta, total_delta) if total_delta else None
        else:
            top_size, total_delta, delta_pct = None, None, None
        out.append({
            "metric": name,
            "total_1200": total_a,
            "total_2400": total_b,
            "delta": total_delta,
            "per_attempt_delta_by_subset_size": per_attempt_delta,
            "subset_size_receiving_most_delta": top_size,
            "delta_pct_in_that_attempt": delta_pct,
        })
    return {"n_attempts_compared": n, "metrics": out}


def two_sheet_verdict(delta: dict[str, Any]) -> dict[str, Any]:
    rt = next((m for m in delta["metrics"] if m["metric"] == "sparrow_ms_runtime_ms"), None)
    if not rt or rt["delta"] is None:
        return {"answer": "NOT PROVEN", "evidence": "missing runtime delta data"}
    top_size = rt["subset_size_receiving_most_delta"]
    pad = rt["per_attempt_delta_by_subset_size"]
    share = rt["delta_pct_in_that_attempt"]
    answer = "YES" if top_size == 2 and (share or 0) >= 50 else "NO"
    return {
        "answer": answer,
        "subset_size_receiving_most_runtime_delta": top_size,
        "runtime_delta_share_pct": share,
        "per_attempt_runtime_delta_ms_by_subset_size": pad,
        "total_runtime_delta_ms": rt["delta"],
        "evidence": (
            f"runtime delta {rt['delta']:.0f} ms; subset_size={top_size} attempt received "
            f"{share}% of it (per-attempt ms delta by subset size: {pad})"
        ),
    }


def _md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return out


def write_markdown_tables(summary: dict[str, Any], outs: dict[int, dict[str, Any]]) -> None:
    L: list[str] = ["# SGH-Q44 extracted per-attempt tables", ""]

    # 1. Baseline confirmation
    L += ["## 1. Baseline confirmation", ""]
    bh = ["run_id", "time_limit_s", "placed", "unplaced", "used_sheets", "ms_attempts",
          "ms_subsets", "ms_runtime_ms", "wall_s", "cde_batch_cand_q", "cde_batch_eng_builds",
          "cde_batch_hazards", "cde_batch_collisions"]
    brows = []
    for t in outs:
        bc = summary["baseline_confirmation"][t]
        brows.append([bc["run_id"], t, bc["placed_count"], bc["unplaced_count"],
                      bc["used_sheet_count"], bc["sparrow_ms_attempts"],
                      bc["sparrow_ms_candidate_subsets"], bc["sparrow_ms_runtime_ms"],
                      bc["wall_time_s"], bc["cde_batch_candidate_queries"],
                      bc["cde_batch_engine_builds"], bc["cde_batch_hazards_registered"],
                      bc["cde_batch_collisions_returned"]])
    L += _md_table(bh, brows) + [""]

    # consistency check
    L += ["### Per-attempt CDE delta sum vs aggregate (consistency)", ""]
    ch = ["run", "counter", "aggregate", "sum_of_attempt_deltas", "residual(post-loop)"]
    crows = []
    for t in outs:
        for name, v in summary["consistency_check"][t].items():
            crows.append([t, name, v["aggregate"], v["sum_of_attempt_deltas"], v["residual"]])
    L += _md_table(ch, crows) + [""]

    # 2. schedule
    L += ["## 2. Candidate subset schedule", ""]
    sh = ["run", "attempt", "subset_indices", "size", "signature", "full_pool",
          "2nd_to_last", "alloc_s", "actual_s", "rem_before_s", "rem_after_s", "deadline_hit"]
    srows = []
    for t in outs:
        for r in summary["schedule_table"][t]:
            srows.append([t, r["attempt_index"], r["subset_indices_original"], r["subset_size"],
                          r["subset_signature"], r["is_full_pool"], r["is_second_to_last"],
                          r["allocated_time_limit_s"], r["actual_runtime_s"],
                          r["remaining_budget_before_s"], r["remaining_budget_after_s"],
                          r["deadline_hit_after_attempt"]])
    L += _md_table(sh, srows) + [""]

    # 3. outcome
    L += ["## 3. Attempt outcome table", ""]
    oh = ["run", "attempt", "core_feasible", "core_status", "placed", "unplaced",
          "used_sheets", "final_pairs", "boundary", "sanitized", "score", "incumbent", "stop_reason"]
    orows = []
    for t in outs:
        for r in summary["outcome_table"][t]:
            orows.append([t, r["attempt_index"], r["core_feasible"], r["core_status"],
                          r["placed_after_sanitize"], r["unplaced_after_sanitize"],
                          r["used_sheet_count"], r["final_pairs"], r["boundary_violations"],
                          r["sanitized"], r["candidate_score"], r["became_incumbent"],
                          r["stop_reason"]])
    L += _md_table(oh, orows) + [""]

    # 4. CDE cost
    L += ["## 4. Attempt-level CDE cost table", ""]
    dh = ["run", "attempt", "size", "actual_ms", "engine_builds_d", "batch_cand_q_d",
          "batch_eng_builds_d", "hazards_d", "collisions_d", "rt%", "cand_q%",
          "batch_eng%", "hazard%", "coll%"]
    drows = []
    for t in outs:
        for r in summary["cde_cost_table"][t]:
            drows.append([t, r["attempt_index"], r["subset_size"], r["actual_runtime_ms"],
                          r["cde_engine_builds_delta"], r["cde_batch_candidate_queries_delta"],
                          r["cde_batch_engine_builds_delta"], r["cde_batch_hazards_registered_delta"],
                          r["cde_batch_collisions_returned_delta"], r["attempt_runtime_pct"],
                          r["candidate_query_pct"], r["batch_engine_build_pct"],
                          r["hazard_registered_pct"], r["collisions_returned_pct"]])
    L += _md_table(dh, drows) + [""]

    # 5. sparrow cost
    L += ["## 5. Attempt-level Sparrow/search cost table", ""]
    ph = ["run", "attempt", "iters", "moves_att", "moves_acc", "rollbacks", "search_calls",
          "search_samples", "coord_steps", "edges_recomputed", "full_rebuilds", "incr_updates"]
    prows = []
    for t in outs:
        for r in summary["sparrow_cost_table"][t]:
            prows.append([t, r["attempt_index"], r["sparrow_iterations"],
                          r["sparrow_moves_attempted"], r["sparrow_moves_accepted"],
                          r["sparrow_rollbacks"], r["sparrow_search_position_calls"],
                          r["sparrow_search_position_samples"], r["search_position_coord_descent_steps"],
                          r["sparrow_graph_edges_recomputed"], r["sparrow_graph_full_rebuilds"],
                          r["sparrow_graph_incremental_updates"]])
    L += _md_table(ph, prows) + [""]

    # 6. delta analysis
    if "delta_analysis_1200_to_2400" in summary:
        L += ["## 6. 1200s vs 2400s delta analysis", ""]
        mh = ["metric", "1200s_total", "2400s_total", "delta", "subset_size_most_delta",
              "delta_pct_in_that_attempt", "per_attempt_delta_by_subset_size"]
        mrows = []
        for m in summary["delta_analysis_1200_to_2400"]["metrics"]:
            mrows.append([m["metric"], m["total_1200"], m["total_2400"], m["delta"],
                          m["subset_size_receiving_most_delta"], m["delta_pct_in_that_attempt"],
                          m["per_attempt_delta_by_subset_size"]])
        L += _md_table(mh, mrows) + [""]
        v = summary.get("two_sheet_extra_runtime_verdict", {})
        L += ["**Did the additional ~599 s in the 2400s run mostly go into the 2-sheet attempt?**", "",
              f"- Answer: **{v.get('answer')}**",
              f"- subset_size receiving most runtime delta: `{v.get('subset_size_receiving_most_runtime_delta')}`",
              f"- runtime delta share in that attempt: `{v.get('runtime_delta_share_pct')}%`",
              f"- evidence: `{v.get('evidence')}`", ""]

    (Q44 / "q44_tables.md").write_text("\n".join(L) + "\n")
    print(f"Wrote {Q44/'q44_tables.md'}")


def build(args) -> int:
    Q44.mkdir(parents=True, exist_ok=True)
    if args.run:
        if not SOLVER_BIN.exists():
            raise SystemExit(f"missing solver binary: {SOLVER_BIN}")
        for t in RUN_TIMES:
            print(f"Running Q42 {t}s solve for Q44 extraction ...")
            run_solver(t)

    outs: dict[int, dict[str, Any]] = {}
    for t in RUN_TIMES:
        o = load_output(t)
        if o is None:
            print(f"WARNING: missing Q42 output for {t}s ({output_path(t)})")
            continue
        if not attempt_rows(o):
            print(f"WARNING: {t}s output has NO sparrow_ms_attempt_diagnostics array "
                  f"(rebuild solver + re-run Q42 benchmark).")
        outs[t] = o

    summary: dict[str, Any] = {
        "task": "SGH-Q44",
        "kind": "per_attempt_multisheet_diagnostics_extractor",
        "run_ids": {t: f"{RUN_ID_PREFIX}_{t}" for t in outs},
        "1200s_run_executed": 1200 in outs,
        "2400s_run_executed": 2400 in outs,
        "baseline_confirmation": {},
        "consistency_check": {},
        "schedule_table": {},
        "outcome_table": {},
        "cde_cost_table": {},
        "sparrow_cost_table": {},
    }
    for t, o in outs.items():
        summary["baseline_confirmation"][t] = baseline_confirmation(t, o)
        summary["consistency_check"][t] = consistency_check(o)
        summary["schedule_table"][t] = schedule_table(o)
        summary["outcome_table"][t] = outcome_table(o)
        summary["cde_cost_table"][t] = cde_cost_table(o)
        summary["sparrow_cost_table"][t] = sparrow_cost_table(o)
        # per-run extracted artifact
        (Q44 / f"q44_attempt_diagnostics_{t}.json").write_text(json.dumps({
            "run_id": f"{RUN_ID_PREFIX}_{t}",
            "time_limit_s": t,
            "attempt_diagnostics_count": od(o).get("sparrow_ms_attempt_diagnostics_count"),
            "attempt_diagnostics_schema_version": od(o).get("sparrow_ms_attempt_diagnostics_schema_version"),
            "attempt_diagnostics": attempt_rows(o),
            "collision_backend_diagnostics": cbd(o),
        }, indent=2))

    if 1200 in outs and 2400 in outs:
        delta = delta_analysis(outs[1200], outs[2400])
        summary["delta_analysis_1200_to_2400"] = delta
        summary["two_sheet_extra_runtime_verdict"] = two_sheet_verdict(delta)

    (Q44 / "q44_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {Q44/'q44_summary.json'}")
    for t in outs:
        print(f"Wrote {Q44/('q44_attempt_diagnostics_%d.json' % t)}")
    if outs:
        write_markdown_tables(summary, outs)

    # console digest
    for t in outs:
        bc = summary["baseline_confirmation"][t]
        print(f"\n=== {t}s : attempts={bc['sparrow_ms_attempts']} "
              f"subsets={bc['sparrow_ms_candidate_subsets']} "
              f"count={bc['attempt_diagnostics_count']} "
              f"runtime_ms={bc['sparrow_ms_runtime_ms']} ===")
        for r in summary["schedule_table"][t]:
            print(f"  attempt {r['attempt_index']} size={r['subset_size']} "
                  f"alloc={r['allocated_time_limit_s']}s actual={r['actual_runtime_s']}s")
    if "two_sheet_extra_runtime_verdict" in summary:
        v = summary["two_sheet_extra_runtime_verdict"]
        print(f"\n2-sheet extra-runtime verdict: {v.get('answer')} "
              f"(subset_size {v.get('subset_size_receiving_most_runtime_delta')} got "
              f"{v.get('runtime_delta_share_pct')}% of the runtime delta)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="store_true",
                   help="(re)run the solver on the Q42 inputs first (long: 1200s+2400s).")
    return build(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
