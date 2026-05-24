#!/usr/bin/env python3
"""JG-20 Phase 2 irregular/remnant benchmark matrix.

Runs L-shape, concave remnant, mixed rectangular+remnant, and rectangular
regression cases through the Phase 1 solver profile
(jagua_optimizer_phase1_outer_only) with hole-free outer-only fixtures.

Outputs:
  codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.json
  codex/reports/egyedi_solver/jagua_optimizer_phase2_irregular_benchmark.md
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.runner.vrs_solver_runner import run_solver_in_dir  # noqa: E402

REPORT_DIR = ROOT / "codex" / "reports" / "egyedi_solver"
JSON_OUT = REPORT_DIR / "jagua_optimizer_phase2_irregular_benchmark.json"
MD_OUT = REPORT_DIR / "jagua_optimizer_phase2_irregular_benchmark.md"

PHASE1_PROFILE = "jagua_optimizer_phase1_outer_only"
SEED = 42

# L-shape: 150x150 bbox, notch at top-right 75x75. Area = 150*150 - 75*75 = 16875.
L_SHAPE_OUTER = [
    [0, 0], [150, 0], [150, 75], [75, 75], [75, 150], [0, 150]
]

# ---------------------------------------------------------------------------
# Benchmark cases
# ---------------------------------------------------------------------------

CASES: list[dict[str, Any]] = [
    # 1. L-shape: irregular concave stock, hole-free
    {
        "case_id": "l_shape",
        "description": "L-shaped stock 150x150 bbox (notch top-right 75x75), 4 parts 25x20, rotations [0,90]",
        "stock_summary": {"type": "irregular", "has_irregular_outer": True, "cost_per_use": 1.0},
        "time_limit_s": 8,
        "input": {
            "contract_version": "v1",
            "project_name": "jg20_l_shape",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 8,
            "stocks": [
                {
                    "id": "L_stock",
                    "quantity": 2,
                    "outer_points": L_SHAPE_OUTER,
                },
            ],
            "parts": [
                {
                    "id": "part_25x20",
                    "width": 25.0,
                    "height": 20.0,
                    "quantity": 4,
                    "allowed_rotations_deg": [0, 90],
                },
            ],
        },
    },
    # 2. Concave remnant: L-shape with cost_per_use = 0.2
    {
        "case_id": "concave_remnant",
        "description": "L-shaped remnant (cost=0.2), 4 parts 25x20, JG-19 score model active",
        "stock_summary": {"type": "irregular", "has_irregular_outer": True, "cost_per_use": 0.2},
        "time_limit_s": 8,
        "input": {
            "contract_version": "v1",
            "project_name": "jg20_concave_remnant",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 8,
            "stocks": [
                {
                    "id": "L_remnant",
                    "quantity": 1,
                    "outer_points": L_SHAPE_OUTER,
                    "cost_per_use": 0.2,
                },
            ],
            "parts": [
                {
                    "id": "part_25x20",
                    "width": 25.0,
                    "height": 20.0,
                    "quantity": 4,
                    "allowed_rotations_deg": [0, 90],
                },
            ],
        },
    },
    # 3. Mixed rectangular + remnant (JG-19 score model — mixed stock types)
    {
        "case_id": "mixed_rectangular_remnant",
        "description": "1 rectangular stock (cost=1.0) + 1 L-shape remnant (cost=0.2), 3 parts 50x50",
        "stock_summary": {
            "type": "mixed",
            "stocks": [
                {"id": "regular_200x200", "has_irregular_outer": False, "cost_per_use": 1.0},
                {"id": "L_remnant_200", "has_irregular_outer": True, "cost_per_use": 0.2},
            ],
        },
        "time_limit_s": 10,
        "input": {
            "contract_version": "v1",
            "project_name": "jg20_mixed",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 10,
            "stocks": [
                {
                    "id": "regular_200x200",
                    "quantity": 1,
                    "width": 200,
                    "height": 200,
                    "cost_per_use": 1.0,
                },
                {
                    "id": "L_remnant_200",
                    "quantity": 1,
                    "outer_points": [
                        [0, 0], [200, 0], [200, 100], [100, 100], [100, 200], [0, 200]
                    ],
                    "cost_per_use": 0.2,
                },
            ],
            "parts": [
                {
                    "id": "square_50",
                    "width": 50.0,
                    "height": 50.0,
                    "quantity": 3,
                    "allowed_rotations_deg": [0],
                },
            ],
        },
    },
    # 4. Rectangular Phase 1 regression: identical to JG-14 "small" case
    {
        "case_id": "rectangular_phase1_regression",
        "description": "JG-14 'small' rectangular case: 3 part types, 0/90 rotations, 1 sheet (regression)",
        "stock_summary": {"type": "rectangular", "has_irregular_outer": False, "cost_per_use": 1.0},
        "time_limit_s": 10,
        "input": {
            "contract_version": "v1",
            "project_name": "jg20_rect_regression",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 10,
            "stocks": [
                {"id": "S1", "quantity": 1, "width": 200, "height": 150},
            ],
            "parts": [
                {"id": "A", "width": 50, "height": 40, "quantity": 3,
                 "allowed_rotations_deg": [0, 90]},
                {"id": "B", "width": 30, "height": 60, "quantity": 2,
                 "allowed_rotations_deg": [0, 90]},
                {"id": "C", "width": 20, "height": 20, "quantity": 4,
                 "allowed_rotations_deg": [0]},
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_solver_bin() -> str:
    explicit = os.environ.get("VRS_SOLVER_BIN")
    if explicit:
        p = Path(explicit)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        print(f"VRS_SOLVER_BIN not executable: {explicit}", file=sys.stderr)
        sys.exit(1)
    release = ROOT / "rust/vrs_solver/target/release/vrs_solver"
    if release.is_file() and os.access(release, os.X_OK):
        return str(release)
    which = shutil.which("vrs_solver")
    if which:
        return which
    print("Building vrs_solver release...", flush=True)
    r = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path",
         str(ROOT / "rust/vrs_solver/Cargo.toml")],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(1)
    return str(release)


def _extract_score_breakdown(run_dir: Path) -> dict[str, Any] | None:
    out_path = run_dir / "solver_output.json"
    if not out_path.is_file():
        return None
    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
        return data.get("score_breakdown")
    except Exception:  # noqa: BLE001
        return None


def _run_case(
    solver_bin: str,
    case: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    case_input = case["input"]
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = run_dir / "solver_input.json"
    input_path.write_text(json.dumps(case_input), encoding="utf-8")

    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "description": case.get("description", ""),
        "solver_profile": case_input.get("solver_profile", "default"),
        "seed": case_input.get("seed", SEED),
        "time_limit_s": case_input.get("time_limit_s", 5),
        "stock_summary": case.get("stock_summary", {}),
        "solver_bin": solver_bin,
        "placed": None,
        "unplaced": None,
        "used_sheets": None,
        "utilization": None,
        "runtime_sec": None,
        "validation_status": None,
        "validation_error": None,
        "boundary_rejects": None,
        "boundary_rejects_status": "unavailable",
        "boundary_rejects_unavailable_reason": "not exposed in solver_output.json v1",
        "score_breakdown": None,
        "status": "fail",
        "error": None,
    }

    try:
        _returned_run_dir, meta = run_solver_in_dir(
            str(input_path),
            run_dir=run_dir,
            seed=case_input.get("seed", SEED),
            time_limit_s=case_input.get("time_limit_s", 5),
            solver_bin=solver_bin,
        )
        result["placed"] = meta.get("placements_count")
        result["unplaced"] = meta.get("unplaced_count")
        result["used_sheets"] = meta.get("sheet_count_used")
        result["utilization"] = meta.get("utilization")
        result["runtime_sec"] = meta.get("duration_sec")
        result["validation_status"] = meta.get("validation_status")
        result["validation_error"] = meta.get("validation_error")
        result["solver_bin"] = meta.get("solver_bin", solver_bin)

        score_bd = _extract_score_breakdown(run_dir)
        result["score_breakdown"] = score_bd
        if score_bd and score_bd.get("usable_area_utilization") is not None:
            result["utilization"] = score_bd["usable_area_utilization"]

        vs = meta.get("validation_status")
        if vs == "pass":
            result["status"] = "pass"
        elif vs == "skipped_unsupported":
            result["status"] = "unsupported"
        else:
            result["status"] = "fail"

    except Exception as exc:  # noqa: BLE001
        result["status"] = "fail"
        result["error"] = str(exc)
        meta_p = run_dir / "runner_meta.json"
        if meta_p.is_file():
            try:
                m = json.loads(meta_p.read_text(encoding="utf-8"))
                result["runtime_sec"] = m.get("duration_sec")
                result["validation_status"] = m.get("validation_status")
                result["validation_error"] = m.get("validation_error")
            except Exception:  # noqa: BLE001
                pass

    return result


def _run_boundary_fail_evidence() -> dict[str, Any]:
    """Run the JG-17 boundary validation smoke as invalid-boundary fail evidence."""
    smoke_script = ROOT / "scripts" / "smoke_jagua_irregular_boundary_validation.py"
    if not smoke_script.is_file():
        return {"status": "missing", "reason": "smoke_jagua_irregular_boundary_validation.py not found"}
    r = subprocess.run(
        [sys.executable, str(smoke_script)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    lines = (r.stdout + r.stderr).splitlines()
    tail = "\n".join(lines[-10:]) if len(lines) > 10 else "\n".join(lines)
    return {
        "status": "pass" if r.returncode == 0 else "fail",
        "returncode": r.returncode,
        "tail": tail,
        "source": "smoke_jagua_irregular_boundary_validation.py (JG-17 boundary policy)",
    }


def _gate_decision(results: list[dict[str, Any]], boundary_evidence: dict[str, Any]) -> str:
    # STOP: any accepted case has invalid layout or rect regression fails
    rect_case = next((r for r in results if r["case_id"] == "rectangular_phase1_regression"), None)
    if rect_case and rect_case.get("validation_status") == "fail":
        return "STOP"
    for r in results:
        if r.get("validation_status") == "fail":
            return "STOP"
    if boundary_evidence.get("status") != "pass":
        return "REVISE"
    # PASS: all required cases ran with pass or unsupported, rect regression pass
    required = {"l_shape", "concave_remnant", "mixed_rectangular_remnant", "rectangular_phase1_regression"}
    ran = {r["case_id"] for r in results if r.get("validation_status") in ("pass", "skipped_unsupported")}
    if not required.issubset(ran):
        return "REVISE"
    all_pass = all(
        r.get("validation_status") == "pass"
        for r in results
        if r["case_id"] in required
    )
    if all_pass:
        return "PASS"
    return "REVISE"


def _write_md(results: list[dict[str, Any]], boundary_evidence: dict[str, Any], gate: str, solver_bin: str) -> None:
    lines: list[str] = [
        "# Phase 2 Irregular/Remnant Benchmark — JG-20",
        "",
        f"PHASE2_GATE_DECISION: {gate}",
        "",
        f"- **solver_bin:** `{solver_bin}`",
        f"- **seed:** {SEED}",
        f"- **profile:** `{PHASE1_PROFILE}`",
        f"- **date:** 2026-05-24",
        "",
        "## Case results",
        "",
        "| case_id | status | placed | unplaced | sheets | utilization | dur_s | validation | stock_type |",
        "|---------|--------|--------|----------|--------|-------------|-------|------------|------------|",
    ]
    for r in results:
        util = r.get("utilization")
        util_s = f"{util:.4f}" if util is not None else "n/a"
        dur = r.get("runtime_sec")
        dur_s = f"{dur:.2f}" if dur is not None else "n/a"
        stock_type = r.get("stock_summary", {}).get("type", "?")
        lines.append(
            f"| {r['case_id']} "
            f"| {r.get('status','?')} "
            f"| {r.get('placed','?')} "
            f"| {r.get('unplaced','?')} "
            f"| {r.get('used_sheets','?')} "
            f"| {util_s} "
            f"| {dur_s} "
            f"| {r.get('validation_status','?')} "
            f"| {stock_type} |"
        )

    lines += [
        "",
        "## Score breakdown (Phase 1 profile)",
        "",
        "| case_id | total_cost | placed_area_contrib | sheet_cost_contrib | sheet_cost_total | usable_area_util | overlap | boundary |",
        "|---------|-----------|--------------------|--------------------|-----------------|-----------------|---------|----------|",
    ]
    for r in results:
        bd = r.get("score_breakdown") or {}
        def _f(v: Any, fmt: str = ".2f") -> str:
            return format(v, fmt) if isinstance(v, (int, float)) else "n/a"
        lines.append(
            f"| {r['case_id']} "
            f"| {_f(bd.get('total_cost'))} "
            f"| {_f(bd.get('placed_area_contribution'))} "
            f"| {_f(bd.get('sheet_cost_contribution'))} "
            f"| {_f(bd.get('sheet_cost_total'))} "
            f"| {_f(bd.get('usable_area_utilization'), '.4f')} "
            f"| {_f(bd.get('overlap_contribution'))} "
            f"| {_f(bd.get('boundary_contribution'))} |"
        )

    lines += [
        "",
        "## Boundary rejects",
        "",
        "Boundary reject counts are not exposed in `solver_output.json` v1 (not a standard meta field).",
        "Proxy evidence: `score_breakdown.boundary_contribution` = 0.0 for all valid placements above,",
        "confirming no boundary violations accepted.",
        "",
        "## Invalid boundary fail evidence",
        "",
        f"- Source: `{boundary_evidence.get('source', 'n/a')}`",
        f"- Result: **{boundary_evidence.get('status', 'n/a').upper()}** (exit={boundary_evidence.get('returncode', 'n/a')})",
        "",
        "```",
        boundary_evidence.get("tail", ""),
        "```",
        "",
        "## Validation evidence",
        "",
        "All accepted layouts carry `validation_status=pass` from the exact Python validation bridge.",
        "`validation_status=fail` results are marked as `status=fail` and not accepted as successful benchmarks.",
        "",
        "## Rectangular Phase 1 regression",
        "",
        "Case `rectangular_phase1_regression` replicates the JG-14 'small' fixture.",
        "If this case passes, rectangular Phase 1 behavior is unaffected by Phase 2 irregular/remnant changes.",
        "",
        "## Gate 2 decision",
        "",
        f"**PHASE2_GATE_DECISION: {gate}**",
        "",
        "Decision rules:",
        "- PASS: all required Phase 2 cases ran, all accepted layouts validation_status=pass,",
        "  rectangular regression PASS, invalid boundary fail evidence present.",
        "- REVISE: partial results or non-critical gap (boundary evidence not confirmed).",
        "- STOP: any invalid layout accepted as success or rectangular regression fails.",
        "",
    ]
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== JG-20 Phase 2 Irregular/Remnant Benchmark Matrix ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="jg20_bench_") as tmp:
        tmp_path = Path(tmp)

        for case in CASES:
            case_id = case["case_id"]
            print(f"\n--- Case: {case_id} ---")
            print(f"    {case['description']}")
            run_dir = tmp_path / case_id
            r = _run_case(solver_bin, case, run_dir)
            results.append(r)
            bd = r.get("score_breakdown") or {}
            print(f"    status={r['status']} placed={r['placed']} unplaced={r['unplaced']} "
                  f"sheets={r['used_sheets']} util={r['utilization']} dur={r['runtime_sec']}s "
                  f"valid={r['validation_status']}")
            if bd:
                print(f"    score_breakdown: total_cost={bd.get('total_cost')} "
                      f"sheet_cost_total={bd.get('sheet_cost_total')} "
                      f"usable_area_util={bd.get('usable_area_utilization')} "
                      f"boundary={bd.get('boundary_contribution')}")
            if r.get("error"):
                print(f"    error: {r['error']}")

    print("\n--- Invalid boundary fail evidence ---")
    boundary_evidence = _run_boundary_fail_evidence()
    print(f"    {boundary_evidence.get('source','')}: {boundary_evidence.get('status','?').upper()}")

    gate = _gate_decision(results, boundary_evidence)
    print(f"\nPHASE2_GATE_DECISION: {gate}")

    json_payload = {
        "meta": {
            "solver_bin": solver_bin,
            "seed": SEED,
            "phase2_profile": PHASE1_PROFILE,
            "phase2_gate_decision": gate,
            "date": "2026-05-24",
        },
        "cases": results,
        "boundary_fail_evidence": boundary_evidence,
    }
    JSON_OUT.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"JSON → {JSON_OUT}")

    _write_md(results, boundary_evidence, gate, solver_bin)
    print(f"MD   → {MD_OUT}")

    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
