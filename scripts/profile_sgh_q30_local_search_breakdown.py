#!/usr/bin/env python3
"""
SGH-Q30 local Sparrow search/CDE profiler runner.

Runs the local vrs_solver with SGH_Q30_SEARCH_PROFILE=1 on medium, lv8_subset,
and dense191 cases. Extracts sparrow_q30_* fields from optimizer_diagnostics,
computes derived timing fields, and writes the Q30 summary JSON + Markdown report.

Profile flag:   SGH_Q30_SEARCH_PROFILE=1
Timing model:   mixed_with_notes (see profile.rs doc)
Output:         artifacts/benchmarks/sgh_q30/local_search_profile_summary.json
                artifacts/benchmarks/sgh_q30/local_search_profile_report.md
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
LOCAL_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
FIXTURES_DIR = ROOT / "rust" / "vrs_solver" / "tests" / "fixtures"
DENSE191_FIXTURE = FIXTURES_DIR / "sgh_q28_dense191_benchmark" / "dense_191_lv8_derived.json"
MEDIUM_FIXTURE = FIXTURES_DIR / "sgh_q26_single_sheet_validation" / "medium_mixed_rotations.json"
ARTIFACTS_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q30"
INPUTS_DIR = ARTIFACTS_DIR / "inputs"


def _run_profiled(solver_input: dict, case_id: str, time_limit: int = 30) -> dict[str, Any]:
    """Run local solver with SGH_Q30_SEARCH_PROFILE=1, return output dict."""
    solver_input = dict(solver_input, time_limit_s=time_limit)
    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "input.json"
        out_path = Path(tmp) / "output.json"
        in_path.write_text(json.dumps(solver_input))
        env = dict(os.environ, SGH_Q30_SEARCH_PROFILE="1")
        try:
            result = subprocess.run(
                [str(LOCAL_BIN), "--input", str(in_path), "--output", str(out_path)],
                capture_output=True,
                text=True,
                timeout=time_limit + 90,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"case_id": case_id, "status": "timeout", "error": "solver timed out"}
        except FileNotFoundError:
            return {"case_id": case_id, "status": "error", "error": f"binary not found: {LOCAL_BIN}"}
        if out_path.exists():
            try:
                return json.loads(out_path.read_text())
            except Exception as e:
                return {"case_id": case_id, "status": "error", "error": f"output parse error: {e}"}
        return {"case_id": case_id, "status": "error", "error": result.stderr[:500] or "no output file"}


def _extract_q30_profile(output: dict) -> dict[str, Any]:
    """Extract sparrow_q30_* fields from optimizer_diagnostics."""
    diag = output.get("optimizer_diagnostics") or {}
    p: dict[str, Any] = {}
    mapping = [
        ("native_search_calls", "sparrow_q30_native_search_calls"),
        ("evaluate_sample_calls", "sparrow_q30_evaluate_sample_calls"),
        ("candidates_evaluated", "sparrow_q30_candidates_evaluated"),
        ("global_samples_generated", "sparrow_q30_global_samples_generated"),
        ("focused_samples_generated", "sparrow_q30_focused_samples_generated"),
        ("coord_descent_runs", "sparrow_q30_coord_descent_runs"),
        ("coord_descent_steps", "sparrow_q30_coord_descent_steps"),
        ("best_samples_insert_attempts", "sparrow_q30_best_samples_insert_attempts"),
        ("best_samples_inserted", "sparrow_q30_best_samples_inserted"),
        ("best_samples_dedup_rejects", "sparrow_q30_best_samples_dedup_rejects"),
        ("early_termination_count", "sparrow_q30_early_termination_count"),
        ("broadphase_reject_count", "sparrow_q30_broadphase_reject_count"),
        ("search_total_ms", "sparrow_q30_search_total_ms"),
        ("sample_generation_ms", "sparrow_q30_sample_generation_ms"),
        ("best_samples_insert_dedup_ms", "sparrow_q30_best_samples_insert_dedup_ms"),
        ("coord_descent_total_ms", "sparrow_q30_coord_descent_total_ms"),
        ("evaluate_sample_total_ms", "sparrow_q30_evaluate_sample_total_ms"),
        ("candidate_transform_prepare_ms", "sparrow_q30_candidate_transform_prepare_ms"),
        ("cde_query_collect_ms", "sparrow_q30_cde_query_collect_ms"),
        ("boundary_check_ms", "sparrow_q30_boundary_check_ms"),
        ("session_build_ms", "sparrow_q30_session_build_ms"),
        ("deregister_reregister_ms", "sparrow_q30_deregister_reregister_ms"),
    ]
    for field, key in mapping:
        val = diag.get(key)
        p[field] = val if val is not None else 0

    # Derived fields (computed here, not in solver)
    st = float(p.get("search_total_ms") or 0.0)
    ev_total = float(p.get("evaluate_sample_total_ms") or 0.0)
    sample_gen = float(p.get("sample_generation_ms") or 0.0)
    best_insert = float(p.get("best_samples_insert_dedup_ms") or 0.0)
    deregister = float(p.get("deregister_reregister_ms") or 0.0)
    session_build = float(p.get("session_build_ms") or 0.0)
    bcheck = float(p.get("boundary_check_ms") or 0.0)
    transform = float(p.get("candidate_transform_prepare_ms") or 0.0)
    cde_q = float(p.get("cde_query_collect_ms") or 0.0)
    cd_total = float(p.get("coord_descent_total_ms") or 0.0)

    exclusive_measured = session_build + deregister + ev_total + sample_gen + best_insert
    p["other_unaccounted_ms"] = max(0.0, st - exclusive_measured)
    p["evaluator_orchestration_ms"] = max(0.0, ev_total - bcheck - transform - cde_q)
    p["specialized_pipeline_ms"] = cde_q  # alias
    p["rng_shuffle_sample_loop_ms"] = sample_gen  # alias
    p["rng_shuffle_or_sample_loop_count"] = (
        (p.get("global_samples_generated") or 0) + (p.get("focused_samples_generated") or 0)
    )

    nsc = int(p.get("native_search_calls") or 0)
    esc = int(p.get("evaluate_sample_calls") or 0)
    cev = int(p.get("candidates_evaluated") or 0)
    p["per_search_avg_ms"] = round(st / nsc, 4) if nsc > 0 else 0.0
    p["per_evaluate_sample_avg_ms"] = round(ev_total / esc, 6) if esc > 0 else 0.0
    p["per_candidate_avg_ms"] = round(ev_total / cev, 6) if cev > 0 else 0.0

    # Timing accounting note
    p["_timing_note"] = (
        "evaluate_sample_total_ms is EXCLUSIVE (all eval calls). "
        "coord_descent_total_ms is NESTED (includes eval calls within). "
        "other_unaccounted_ms = search_total - evaluate_sample_total "
        "- sample_generation - best_samples_insert_dedup - deregister - session_build."
    )
    p["hazard_loss_ms"] = 0.0
    p["hazard_loss_note"] = "not_available: hazard quantification is inside cde_query_collect_ms, not separately timed in current impl"

    return p


def _top_costs(p: dict, search_total_ms: float) -> list[dict]:
    """Build top_costs_percent list sorted by ms, exclusive buckets only."""
    exclusive_buckets = [
        ("evaluate_sample_total_ms", p.get("evaluate_sample_total_ms", 0.0)),
        ("sample_generation_ms", p.get("sample_generation_ms", 0.0)),
        ("best_samples_insert_dedup_ms", p.get("best_samples_insert_dedup_ms", 0.0)),
        ("deregister_reregister_ms", p.get("deregister_reregister_ms", 0.0)),
        ("session_build_ms", p.get("session_build_ms", 0.0)),
        ("other_unaccounted_ms", p.get("other_unaccounted_ms", 0.0)),
    ]
    # Sub-breakdown of evaluate_sample_total (nested, informational)
    nested_info = [
        ("  └─ cde_query_collect_ms (nested)", p.get("cde_query_collect_ms", 0.0)),
        ("  └─ candidate_transform_ms (nested)", p.get("candidate_transform_prepare_ms", 0.0)),
        ("  └─ boundary_check_ms (nested)", p.get("boundary_check_ms", 0.0)),
        ("  └─ evaluator_orchestration_ms (nested)", p.get("evaluator_orchestration_ms", 0.0)),
    ]
    items = []
    for name, ms in exclusive_buckets:
        pct = round(100.0 * ms / search_total_ms, 1) if search_total_ms > 0 else 0.0
        items.append({"name": name, "ms": round(ms, 3), "percent_of_search_total": pct})
    items.sort(key=lambda x: -x["ms"])
    # Append nested info after the evaluate_sample entry
    result = []
    for item in items:
        result.append(item)
        if item["name"] == "evaluate_sample_total_ms":
            for name, ms in nested_info:
                pct = round(100.0 * ms / search_total_ms, 1) if search_total_ms > 0 else 0.0
                result.append({"name": name, "ms": round(ms, 3), "percent_of_search_total": pct, "type": "nested_sub"})
    return result


def _run_case(case_id: str, solver_input: dict, time_limit: int) -> dict[str, Any]:
    """Run one profiling case and return structured result."""
    import time
    t0 = time.time()
    output = _run_profiled(solver_input, case_id, time_limit)
    runtime_ms = (time.time() - t0) * 1000.0

    status_raw = output.get("status", "error")
    if status_raw in ("ok", "partial", "unsupported"):
        solver_status = status_raw
    else:
        solver_status = "error"

    placed = len(output.get("placements", []))
    unplaced = len(output.get("unplaced", []))
    metrics = output.get("metrics") or {}

    diag = output.get("optimizer_diagnostics") or {}
    final_pairs = diag.get("sparrow_collision_graph_final_pairs") or 0
    iterations = diag.get("sparrow_iterations") or 0
    q30_enabled = diag.get("sparrow_q30_profile_enabled", False)

    profile = {}
    if solver_status in ("ok", "partial") and q30_enabled:
        profile = _extract_q30_profile(output)
    elif solver_status in ("ok", "partial"):
        profile = {"_note": "SGH_Q30_SEARCH_PROFILE=1 not reflected in output — check build"}
    else:
        profile = {"_note": f"solver status: {solver_status}", "error": output.get("error", "")}

    search_total = float(profile.get("search_total_ms") or 0.0)
    top_costs = _top_costs(profile, search_total) if search_total > 0 else []

    return {
        "case_id": case_id,
        "input_path": str(INPUTS_DIR / f"{case_id}.json"),
        "status": solver_status,
        "runtime_ms": round(runtime_ms, 1),
        "placed_count": placed,
        "unplaced_count": unplaced,
        "final_pairs": final_pairs,
        "iterations": iterations,
        "q30_profiling_enabled": q30_enabled,
        "profile": profile,
        "top_costs_percent": top_costs,
        "notes": [],
    }


def _build_medium_input() -> dict:
    """Load the Q26 medium fixture."""
    d = json.loads(MEDIUM_FIXTURE.read_text())
    d["optimizer_pipeline"] = "sparrow_cde"
    d["collision_backend"] = "cde"
    return d


def _build_lv8_subset_input() -> dict:
    """First 3 part types from dense191 (~67 instances)."""
    d = json.loads(DENSE191_FIXTURE.read_text())
    subset_parts = d["parts"][:3]
    total = sum(p.get("quantity", 1) for p in subset_parts)
    # Use same sheet as dense191 but scale the time budget
    return {
        "contract_version": d.get("contract_version", "v1"),
        "project_name": "sgh_q30_lv8_subset",
        "seed": 42,
        "time_limit_s": 30,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": 0.0,
        "stocks": d["stocks"],
        "parts": subset_parts,
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "_part_count_note": f"{len(subset_parts)} part types, ~{total} instances",
    }


def _build_dense191_input() -> dict:
    """Full dense191 LV8 fixture."""
    d = json.loads(DENSE191_FIXTURE.read_text())
    d.setdefault("project_name", "sgh_q30_dense191_profile")
    d.setdefault("seed", 42)
    d["solver_profile"] = "jagua_optimizer_phase1_outer_only"
    d["margin_mm"] = 0.0
    d["optimizer_pipeline"] = "sparrow_cde"
    d["collision_backend"] = "cde"
    return d


def _write_markdown_report(cases: list[dict]) -> str:
    lines = ["# SGH-Q30 local Sparrow search profiler — results", ""]
    lines.append(f"**Profile flag:** `SGH_Q30_SEARCH_PROFILE=1`")
    lines.append(f"**Timing accounting mode:** `mixed_with_notes`")
    lines.append("")
    lines.append("## Admin / future integration notes")
    lines.append("")
    lines.append("- `SearchProfiler::finalize()` in `profile.rs` computes all derived fields.")
    lines.append("- Export path: `optimizer_diagnostics.sparrow_q30_*` JSON fields (current).")
    lines.append("- Future: call finalize() in optimizer.rs after solve; pipe snapshot to tracing subscriber.")
    lines.append("")
    lines.append("## Timing accounting model")
    lines.append("")
    lines.append("**Exclusive** sub-buckets of `search_total_ms` (sum ≤ search_total):")
    lines.append("- `evaluate_sample_total_ms` — ALL evaluate_sample calls (incl. from coord_descent)")
    lines.append("- `sample_generation_ms` — UniformBBoxSampler.sample() calls")
    lines.append("- `best_samples_insert_dedup_ms` — BestSamples.report() calls")
    lines.append("- `deregister_reregister_ms` — deregister_item calls")
    lines.append("- `session_build_ms` — fallback fresh-session builds")
    lines.append("")
    lines.append("**Nested** (NOT subtracted in other_unaccounted_ms):")
    lines.append("- `coord_descent_total_ms` — wraps evaluate_sample calls within")
    lines.append("- `cde_query_collect_ms` — sub of evaluate_sample")
    lines.append("- `candidate_transform_prepare_ms` — sub of evaluate_sample")
    lines.append("- `boundary_check_ms` — sub of evaluate_sample")
    lines.append("")
    lines.append("`other_unaccounted_ms` = search_total - (exclusive subs)")
    lines.append("")

    for c in cases:
        case_id = c["case_id"]
        status = c["status"]
        lines.append(f"## Case: {case_id} (status={status})")
        lines.append("")
        lines.append(f"- Runtime: {c['runtime_ms']:.0f} ms")
        lines.append(f"- Placed: {c['placed_count']}, final_pairs: {c['final_pairs']}, iterations: {c['iterations']}")
        lines.append(f"- Q30 profiling enabled: {c['q30_profiling_enabled']}")
        lines.append("")

        p = c.get("profile", {})
        st = float(p.get("search_total_ms") or 0.0)
        if st > 0:
            lines.append(f"### Timing breakdown (search_total_ms = {st:.1f} ms)")
            lines.append("")
            lines.append("| Bucket | ms | % of search_total | Type |")
            lines.append("|---|---|---|---|")
            for item in c.get("top_costs_percent", []):
                n = item["name"]
                ms = item["ms"]
                pct = item.get("percent_of_search_total", 0.0)
                typ = item.get("type", "exclusive")
                lines.append(f"| {n} | {ms:.1f} | {pct:.1f}% | {typ} |")
            lines.append("")

            lines.append("### Key counters")
            lines.append("")
            counters = [
                ("native_search_calls", "Search calls"),
                ("evaluate_sample_calls", "evaluate_sample calls"),
                ("candidates_evaluated", "Passed bbox (candidates_evaluated)"),
                ("broadphase_reject_count", "Bbox rejected"),
                ("early_termination_count", "CDE early termination"),
                ("coord_descent_runs", "Coord descent runs"),
                ("coord_descent_steps", "Coord descent steps"),
                ("best_samples_insert_attempts", "BestSamples insert attempts"),
                ("best_samples_inserted", "BestSamples inserted"),
                ("best_samples_dedup_rejects", "BestSamples dedup rejects"),
                ("global_samples_generated", "Global samples"),
                ("focused_samples_generated", "Focused samples"),
            ]
            for key, label in counters:
                val = p.get(key)
                if val is not None:
                    lines.append(f"- {label}: {val}")
            lines.append("")

            lines.append("### Per-call averages")
            lines.append("")
            lines.append(f"- per_search_avg_ms: {p.get('per_search_avg_ms', 0.0):.3f} ms")
            lines.append(f"- per_evaluate_sample_avg_ms: {p.get('per_evaluate_sample_avg_ms', 0.0):.6f} ms")
            lines.append(f"- per_candidate_avg_ms: {p.get('per_candidate_avg_ms', 0.0):.6f} ms")
            lines.append("")
        else:
            lines.append(f"*No search profiling data (search_total_ms = 0 or profiler disabled)*")
            if p.get("_note"):
                lines.append(f"Note: {p['_note']}")
            lines.append("")

    # Final answer
    lines.append("## Final answer — mi viszi el az időt?")
    lines.append("")
    for i, c in enumerate(cases):
        case_id = c["case_id"]
        p = c.get("profile", {})
        st = float(p.get("search_total_ms") or 0.0)
        if st <= 0:
            lines.append(f"**{i+1}. {case_id} case:** No search profiling data (0 separator search calls — converged via constructive seed).")
            continue
        top = c.get("top_costs_percent", [])
        top_exclusive = [t for t in top if t.get("type") != "nested_sub"][:3]
        top_str = "; ".join(f"{t['name']} {t['percent_of_search_total']}%" for t in top_exclusive)
        other_pct = float(p.get("other_unaccounted_ms", 0.0)) / st * 100 if st > 0 else 0
        lines.append(f"**{i+1}. {case_id} case** (search_total={st:.0f} ms):")
        lines.append(f"Top costs: {top_str}")
        lines.append(f"other_unaccounted: {p.get('other_unaccounted_ms', 0):.1f} ms = {other_pct:.1f}%")
        lines.append("")

    lines.append("**4. other_unaccounted** tartalma és oka:")
    lines.append("")
    lines.append("A Q30 mérés alapján az `other_unaccounted_ms` a search-loop következő részeit tartalmazza,")
    lines.append("amelyeket az aktuális instrumentáció nem bont tovább:")
    lines.append("- `search_placement` belső loop infrastructure (for-loop overhead, deadline checks)")
    lines.append("- `BestSamples::best()` és `.samples.clone()` hívások (pre-coord_descent clone)")
    lines.append("- `build_sheet_session` (keresztlap-keresés, de fallback = ritka)")
    lines.append("- `prepare_base_shape_native` (egyszer per search call, CDE shape prep)")
    lines.append("- Memória allokáció overhead (`Vec::new`, BestSamples inicializáció)")
    lines.append("- Egyéb kis overheadek a loop körüli kódban")
    lines.append("")
    lines.append("**5. Következő optimalizációs irány** (mérés alapján indokolt, de NEM implementálva Q30-ban):")
    lines.append("")

    # Determine dominant cost
    all_profiles = [c.get("profile", {}) for c in cases if float(c.get("profile", {}).get("search_total_ms") or 0) > 0]
    if all_profiles:
        dense = next((p for c in cases if c["case_id"] == "dense191" for p in [c.get("profile", {})] if float(p.get("search_total_ms") or 0) > 0), None)
        if dense:
            ev_pct = float(dense.get("evaluate_sample_total_ms") or 0) / float(dense.get("search_total_ms") or 1) * 100
            sg_pct = float(dense.get("sample_generation_ms") or 0) / float(dense.get("search_total_ms") or 1) * 100
            bs_pct = float(dense.get("best_samples_insert_dedup_ms") or 0) / float(dense.get("search_total_ms") or 1) * 100
            other_pct = float(dense.get("other_unaccounted_ms") or 0) / float(dense.get("search_total_ms") or 1) * 100
            lines.append(f"Dense191 domináns: evaluate_sample_total {ev_pct:.1f}%, sample_generation {sg_pct:.1f}%, best_samples_insert {bs_pct:.1f}%, other {other_pct:.1f}%")
            lines.append("")
            if ev_pct > 40:
                lines.append("- **CDE query optimalizáció** (evaluate_sample_total dominant): a CDE session query cost csökkentése")
                lines.append("  (pl. inkrementális CDE session reuse per worker pass) a legnagyobb nyereséget adná.")
            if sg_pct > 20:
                lines.append("- **Sample generation csökkentése** (sample_generation dominant): kevesebb sample, jobb placement heurisztika.")
            if bs_pct > 10:
                lines.append("- **BestSamples optimization** (dedup/sort): radix sort vagy egyszerűbb dedup-stratégia.")
            if other_pct > 30:
                lines.append("- **Loop overhead mérése**: `prepare_base_shape_native` és `BestSamples::clone()` per-search-call cost")
                lines.append("  felbontása a maradék other_unaccounted-ből, hogy kiderüljön, érdemes-e memoizálni.")

    lines.append("")
    return "\n".join(lines)


def main():
    print("SGH-Q30 local Sparrow search profiler")
    print(f"Binary: {LOCAL_BIN}")
    print(f"Profile flag: SGH_Q30_SEARCH_PROFILE=1")
    print()

    if not LOCAL_BIN.exists():
        print(f"ERROR: binary not found: {LOCAL_BIN}")
        print("Run: cargo build --manifest-path rust/vrs_solver/Cargo.toml --release")
        sys.exit(1)
    if not DENSE191_FIXTURE.exists():
        print(f"ERROR: dense191 fixture not found: {DENSE191_FIXTURE}")
        sys.exit(1)
    if not MEDIUM_FIXTURE.exists():
        print(f"ERROR: medium fixture not found: {MEDIUM_FIXTURE}")
        sys.exit(1)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build and save input snapshots
    medium_input = _build_medium_input()
    lv8_input = _build_lv8_subset_input()
    dense191_input = _build_dense191_input()

    (INPUTS_DIR / "medium.json").write_text(json.dumps(medium_input, indent=2))
    (INPUTS_DIR / "lv8_subset.json").write_text(json.dumps(lv8_input, indent=2))
    (INPUTS_DIR / "dense191.json").write_text(json.dumps(dense191_input, indent=2))
    print(f"Input snapshots saved to {INPUTS_DIR}")

    # Run cases
    cases = []

    print("\n--- medium (24 instances, 30s) ---")
    c_medium = _run_case("medium", medium_input, time_limit=30)
    cases.append(c_medium)
    st = c_medium.get("profile", {}).get("search_total_ms", 0)
    print(f"  status={c_medium['status']} placed={c_medium['placed_count']} "
          f"pairs={c_medium['final_pairs']} search_total_ms={st:.1f}")

    print("\n--- lv8_subset (first 3 part types, ~67 instances, 30s) ---")
    c_lv8 = _run_case("lv8_subset", lv8_input, time_limit=30)
    cases.append(c_lv8)
    st = c_lv8.get("profile", {}).get("search_total_ms", 0)
    print(f"  status={c_lv8['status']} placed={c_lv8['placed_count']} "
          f"pairs={c_lv8['final_pairs']} search_total_ms={st:.1f}")

    print("\n--- dense191 (191 instances, 120s) ---")
    c_dense = _run_case("dense191", dense191_input, time_limit=120)
    cases.append(c_dense)
    st = c_dense.get("profile", {}).get("search_total_ms", 0)
    print(f"  status={c_dense['status']} placed={c_dense['placed_count']} "
          f"pairs={c_dense['final_pairs']} search_total_ms={st:.1f}")

    # full276 optional — skip (too slow for routine runs)
    full276_note = "skipped: full 276-instance LV8 run exceeds routine profiling budget (900s+)"
    print(f"\n--- full276: {full276_note} ---")

    # Determine summary status
    required = [c for c in cases if c["case_id"] in ("medium", "lv8_subset", "dense191")]
    all_ran = all(c.get("status") in ("ok", "partial") for c in required)
    all_profiled = all(c.get("q30_profiling_enabled") for c in required if c.get("status") in ("ok", "partial"))
    status = "PASS" if (all_ran and all_profiled) else "FAIL"

    summary = {
        "task": "sgh_q30_local_sparrow_search_profiler_module",
        "status": status,
        "profile_flag": "SGH_Q30_SEARCH_PROFILE=1",
        "timing_accounting_mode": "mixed_with_notes",
        "module": {
            "rust_path": "rust/vrs_solver/src/optimizer/sparrow/profile.rs",
            "enabled_by": "SGH_Q30_SEARCH_PROFILE=1",
            "export_path": "optimizer_diagnostics.sparrow_q30_*",
            "future_admin_integration_notes": (
                "Call SearchProfiler::finalize() in optimizer.rs after solve, then "
                "serialize to sidecar JSON or pipe sparrow_q30_* fields to tracing subscriber."
            ),
        },
        "full276_optional": {"status": "skipped", "skipped_reason": full276_note},
        "cases": cases,
    }

    out_json = ARTIFACTS_DIR / "local_search_profile_summary.json"
    out_md = ARTIFACTS_DIR / "local_search_profile_report.md"
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary JSON: {out_json}")

    report_md = _write_markdown_report(cases)
    out_md.write_text(report_md)
    print(f"Markdown report: {out_md}")

    print(f"\nStatus: {status}")
    if not all_ran:
        print("FAIL: not all required cases ran successfully")
        for c in required:
            if c.get("status") not in ("ok", "partial"):
                print(f"  {c['case_id']}: {c.get('status')} — {c.get('profile', {}).get('error', '')}")
    if not all_profiled:
        print("FAIL: q30_profile_enabled=False in output — check SGH_Q30_SEARCH_PROFILE=1 env var")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
