#!/usr/bin/env python3
"""JG-14 Phase 1 rectangular/no-hole benchmark matrix.

Runs smoke / small / medium / realistic_no_hole fixture cases through the
Phase 1 solver profile (jagua_optimizer_phase1_outer_only) and optionally
through the row/cursor fallback for baseline compare.

Outputs:
  codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.json
  codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md
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
JSON_OUT = REPORT_DIR / "jagua_optimizer_phase1_rectangular_benchmark.json"
MD_OUT = REPORT_DIR / "jagua_optimizer_phase1_rectangular_benchmark.md"

PHASE1_PROFILE = "jagua_optimizer_phase1_outer_only"
SEED = 42

# ---------------------------------------------------------------------------
# Benchmark fixtures
# ---------------------------------------------------------------------------

CASES: list[dict[str, Any]] = [
    # --- smoke: tiny fixture, all must fit ---
    {
        "case_id": "smoke",
        "description": "Tiny 2-part fixture, 1 sheet, all must fit",
        "time_limit_s": 5,
        "input": {
            "contract_version": "v1",
            "project_name": "jg14_smoke",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 5,
            "stocks": [
                {"id": "S1", "quantity": 1, "width": 100, "height": 100},
            ],
            "parts": [
                {"id": "A", "width": 30, "height": 30, "quantity": 2,
                 "allowed_rotations_deg": [0]},
            ],
        },
    },
    # --- small: multiple part types, rotations, all or most fit ---
    {
        "case_id": "small",
        "description": "3 part types, 0/90 rotations, 1 sheet",
        "time_limit_s": 10,
        "input": {
            "contract_version": "v1",
            "project_name": "jg14_small",
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
    # --- medium: multi-sheet, exercises sheet count ---
    {
        "case_id": "medium",
        "description": "Multi-sheet: 6 parts × 70×70 on 3 × 100×100 sheets",
        "time_limit_s": 10,
        "input": {
            "contract_version": "v1",
            "project_name": "jg14_medium",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 10,
            "stocks": [
                {"id": "S1", "quantity": 3, "width": 100, "height": 100},
            ],
            "parts": [
                {"id": "A", "width": 70, "height": 70, "quantity": 6,
                 "allowed_rotations_deg": [0]},
            ],
        },
    },
    # --- realistic_no_hole: larger fixture, multiple part types, multi-sheet ---
    {
        "case_id": "realistic_no_hole",
        "description": "Larger synthetic no-hole fixture: 5 part types, 4 sheets",
        "time_limit_s": 15,
        "input": {
            "contract_version": "v1",
            "project_name": "jg14_realistic",
            "solver_profile": PHASE1_PROFILE,
            "seed": SEED,
            "time_limit_s": 15,
            "stocks": [
                {"id": "S1", "quantity": 4, "width": 300, "height": 200},
            ],
            "parts": [
                {"id": "A", "width": 80, "height": 60, "quantity": 5,
                 "allowed_rotations_deg": [0, 90]},
                {"id": "B", "width": 50, "height": 50, "quantity": 8,
                 "allowed_rotations_deg": [0]},
                {"id": "C", "width": 120, "height": 40, "quantity": 4,
                 "allowed_rotations_deg": [0, 90]},
                {"id": "D", "width": 30, "height": 70, "quantity": 6,
                 "allowed_rotations_deg": [0, 90]},
                {"id": "E", "width": 100, "height": 80, "quantity": 3,
                 "allowed_rotations_deg": [0, 90]},
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


def _run_case(
    solver_bin: str,
    case_input: dict[str, Any],
    run_dir: Path,
    *,
    label: str,
) -> dict[str, Any]:
    """Run one solver case; return result dict."""
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = run_dir / "solver_input.json"
    input_path.write_text(json.dumps(case_input), encoding="utf-8")

    result: dict[str, Any] = {
        "label": label,
        "solver_profile": case_input.get("solver_profile", "default_cursor"),
        "seed": case_input.get("seed", SEED),
        "time_limit_s": case_input.get("time_limit_s", 5),
        "allowed_rotations_summary": _rotations_summary(case_input),
        "solver_bin": solver_bin,
        "placed_count": None,
        "unplaced_count": None,
        "sheet_count_used": None,
        "utilization": None,
        "duration_sec": None,
        "validation_status": None,
        "validation_error": None,
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
        result["placed_count"] = meta.get("placements_count")
        result["unplaced_count"] = meta.get("unplaced_count")
        result["sheet_count_used"] = meta.get("sheet_count_used")
        result["utilization"] = meta.get("utilization")
        result["duration_sec"] = meta.get("duration_sec")
        result["validation_status"] = meta.get("validation_status")
        result["validation_error"] = meta.get("validation_error")
        result["solver_bin"] = meta.get("solver_bin", solver_bin)

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
        # Try to recover meta from disk
        meta_path = run_dir / "runner_meta.json"
        if meta_path.is_file():
            try:
                m = json.loads(meta_path.read_text(encoding="utf-8"))
                result["duration_sec"] = m.get("duration_sec")
                result["validation_status"] = m.get("validation_status")
                result["validation_error"] = m.get("validation_error")
            except Exception:  # noqa: BLE001
                pass

    return result


def _rotations_summary(case_input: dict[str, Any]) -> str:
    parts = case_input.get("parts", [])
    rot_sets = set()
    for p in parts:
        rots = tuple(sorted(p.get("allowed_rotations_deg", [0])))
        rot_sets.add(rots)
    if len(rot_sets) == 1:
        return str(list(rot_sets)[0])
    return "; ".join(str(list(s)) for s in sorted(rot_sets))


def _baseline_input(phase1_input: dict[str, Any]) -> dict[str, Any]:
    """Remove solver_profile to trigger the row/cursor fallback path."""
    inp = dict(phase1_input)
    inp.pop("solver_profile", None)
    inp["project_name"] = inp.get("project_name", "") + "_baseline"
    return inp


def _phase1_gate_decision(results: list[dict[str, Any]]) -> str:
    """
    PASS: all phase1 cases have validation_status=pass.
    REVISE: some metrics missing or partial, but no invalid layout.
    STOP: any phase1 case accepted an invalid layout (validation_status=fail).
    """
    phase1 = [r for r in results if r.get("label", "").startswith("phase1_")]
    if not phase1:
        return "STOP"
    for r in phase1:
        vs = r.get("validation_status")
        if vs == "fail":
            return "STOP"
    all_pass = all(r.get("validation_status") == "pass" for r in phase1)
    if all_pass:
        return "PASS"
    return "REVISE"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== JG-14 Phase 1 Rectangular Benchmark Matrix ===")
    solver_bin = _resolve_solver_bin()
    print(f"solver_bin: {solver_bin}")

    all_results: list[dict[str, Any]] = []
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="jg14_bench_") as tmp:
        tmp_path = Path(tmp)

        for case in CASES:
            case_id = case["case_id"]
            print(f"\n--- Case: {case_id} ---")
            print(f"    {case['description']}")

            # Phase 1 run
            p1_run_dir = tmp_path / f"{case_id}_phase1"
            p1_result = _run_case(
                solver_bin,
                case["input"],
                p1_run_dir,
                label=f"phase1_{case_id}",
            )
            p1_result["case_id"] = case_id
            p1_result["baseline_status"] = None
            p1_result["baseline_metrics_or_reason"] = None
            all_results.append(p1_result)
            print(f"    phase1  → status={p1_result['status']} "
                  f"placed={p1_result['placed_count']} "
                  f"unplaced={p1_result['unplaced_count']} "
                  f"sheets={p1_result['sheet_count_used']} "
                  f"util={p1_result['utilization']} "
                  f"dur={p1_result['duration_sec']}s "
                  f"valid={p1_result['validation_status']}")

            # Baseline run (row/cursor fallback — no solver_profile)
            b_input = _baseline_input(case["input"])
            b_run_dir = tmp_path / f"{case_id}_baseline"
            b_result = _run_case(
                solver_bin,
                b_input,
                b_run_dir,
                label=f"baseline_{case_id}",
            )
            b_result["case_id"] = case_id
            all_results.append(b_result)
            print(f"    baseline→ status={b_result['status']} "
                  f"placed={b_result['placed_count']} "
                  f"unplaced={b_result['unplaced_count']} "
                  f"sheets={b_result['sheet_count_used']} "
                  f"util={b_result['utilization']} "
                  f"dur={b_result['duration_sec']}s "
                  f"valid={b_result['validation_status']}")

            # Annotate phase1 result with baseline comparison
            if b_result["status"] == "pass":
                p1_result["baseline_status"] = "available"
                p1_result["baseline_metrics_or_reason"] = {
                    "placed_count": b_result["placed_count"],
                    "unplaced_count": b_result["unplaced_count"],
                    "sheet_count_used": b_result["sheet_count_used"],
                    "utilization": b_result["utilization"],
                    "duration_sec": b_result["duration_sec"],
                }
            elif b_result["status"] == "unsupported":
                p1_result["baseline_status"] = "unavailable"
                p1_result["baseline_metrics_or_reason"] = "baseline run returned unsupported"
            else:
                p1_result["baseline_status"] = "unavailable"
                p1_result["baseline_metrics_or_reason"] = (
                    f"baseline run failed: {b_result.get('error') or b_result.get('validation_error')}"
                )

    gate = _phase1_gate_decision(all_results)
    print(f"\nPHASE1_GATE_DECISION: {gate}")

    # Build JSON summary (phase1 cases only, with baseline annotation)
    phase1_results = [r for r in all_results if r.get("label", "").startswith("phase1_")]
    json_payload = {
        "meta": {
            "solver_bin": solver_bin,
            "seed": SEED,
            "phase1_profile": PHASE1_PROFILE,
            "phase1_gate_decision": gate,
            "baseline_compare": "row_cursor_fallback (no solver_profile)",
        },
        "cases": phase1_results,
    }
    JSON_OUT.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"JSON → {JSON_OUT}")

    # Build MD summary
    _write_md(phase1_results, gate, solver_bin)
    print(f"MD   → {MD_OUT}")

    return 0 if gate == "PASS" else 1


def _write_md(phase1_results: list[dict[str, Any]], gate: str, solver_bin: str) -> None:
    lines: list[str] = [
        "# Phase 1 Rectangular Benchmark — JG-14",
        "",
        f"PHASE1_GATE_DECISION: {gate}",
        "",
        f"- **solver_bin:** `{solver_bin}`",
        f"- **seed:** {SEED}",
        f"- **profile:** `{PHASE1_PROFILE}`",
        f"- **baseline:** row/cursor fallback (no `solver_profile`)",
        "",
        "## Case results",
        "",
        "| case_id | status | placed | unplaced | sheets | utilization | dur_s | validation | baseline_status |",
        "|---------|--------|--------|----------|--------|-------------|-------|------------|-----------------|",
    ]
    for r in phase1_results:
        util = r.get("utilization")
        util_s = f"{util:.3f}" if util is not None else "n/a"
        dur = r.get("duration_sec")
        dur_s = f"{dur:.2f}" if dur is not None else "n/a"
        lines.append(
            f"| {r.get('case_id','?')} "
            f"| {r.get('status','?')} "
            f"| {r.get('placed_count','?')} "
            f"| {r.get('unplaced_count','?')} "
            f"| {r.get('sheet_count_used','?')} "
            f"| {util_s} "
            f"| {dur_s} "
            f"| {r.get('validation_status','?')} "
            f"| {r.get('baseline_status','?')} |"
        )
    lines += [
        "",
        "## Baseline compare",
        "",
        "Baseline: row/cursor fallback path in `adapter.rs` (no `solver_profile` set).",
        "This is the only repo-supported alternative solver path.",
        "",
        "| case_id | baseline_placed | baseline_sheets | baseline_util | baseline_dur_s |",
        "|---------|----------------|-----------------|---------------|----------------|",
    ]
    for r in phase1_results:
        bs = r.get("baseline_metrics_or_reason")
        if isinstance(bs, dict):
            bp = bs.get("placed_count", "n/a")
            bsh = bs.get("sheet_count_used", "n/a")
            bu = bs.get("utilization")
            bu_s = f"{bu:.3f}" if bu is not None else "n/a"
            bd = bs.get("duration_sec")
            bd_s = f"{bd:.2f}" if bd is not None else "n/a"
        else:
            bp = bsh = bu_s = bd_s = "unavailable"
        lines.append(
            f"| {r.get('case_id','?')} | {bp} | {bsh} | {bu_s} | {bd_s} |"
        )

    lines += [
        "",
        "## Validation evidence",
        "",
        "All accepted layouts carry `validation_status=pass` from the exact validation bridge.",
        "Any `validation_status=fail` case is reported as status=fail and not accepted as success.",
        "",
        "## Phase 1 gate decision",
        "",
        f"**PHASE1_GATE_DECISION: {gate}**",
        "",
        "Decision rules:",
        "- PASS: all required fixtures ran, all accepted layouts validation_status=pass.",
        "- REVISE: infrastructure works, but quality/metrics need improvement.",
        "- STOP: any invalid layout accepted (validation_status=fail).",
        "",
    ]
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
